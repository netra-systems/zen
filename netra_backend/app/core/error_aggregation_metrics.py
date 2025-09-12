"""Alert engine and metrics reporting for error aggregation.

Provides intelligent alerting based on error patterns and trends,
with configurable rules and cooldown mechanisms.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_aggregation_base import (
    AlertRule,
    AlertSeverity,
    ErrorAlert,
    ErrorPattern,
    ErrorTrend,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertEngine:
    """Generates alerts based on error patterns and trends."""
    
    def __init__(self) -> None:
        """Initialize alert engine."""
        self._initialize_state()
        self._setup_default_rules()
    
    def _initialize_state(self) -> None:
        """Initialize engine state."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[ErrorAlert] = []
        self.alert_history: Dict[str, datetime] = {}
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules."""
        self.rules = {
            'high_error_rate': self._create_high_error_rate_rule(),
            'critical_error_spike': self._create_critical_spike_rule(),
            'sustained_errors': self._create_sustained_errors_rule(),
            'new_error_pattern': self._create_new_pattern_rule()
        }
    
    def _create_high_error_rate_rule(self) -> AlertRule:
        """Create high error rate alert rule."""
        params = self._get_high_error_rate_params()
        return self._build_alert_rule(**params)
    
    def _get_high_error_rate_params(self) -> Dict:
        """Get parameters for high error rate rule."""
        return {
            'rule_id': 'high_error_rate', 'name': 'High Error Rate',
            'description': 'Error rate exceeds threshold',
            'condition': 'pattern.count > 50 and window_minutes <= 60',
            'severity': AlertSeverity.HIGH, 'threshold_count': 50, 'time_window_minutes': 60
        }
    
    def _create_critical_spike_rule(self) -> AlertRule:
        """Create critical error spike alert rule."""
        params = self._get_critical_spike_params()
        return self._build_alert_rule(**params)
    
    def _get_critical_spike_params(self) -> Dict:
        """Get parameters for critical spike rule."""
        return {
            'rule_id': 'critical_error_spike', 'name': 'Critical Error Spike',
            'description': 'Sudden spike in critical errors',
            'condition': 'trend.is_spike and pattern.severity_distribution.get("critical", 0) > 0',
            'severity': AlertSeverity.CRITICAL, 'time_window_minutes': 30
        }
    
    def _create_sustained_errors_rule(self) -> AlertRule:
        """Create sustained error pattern alert rule."""
        params = self._get_sustained_errors_params()
        return self._build_alert_rule(**params)
    
    def _get_sustained_errors_params(self) -> Dict:
        """Get parameters for sustained errors rule."""
        return {
            'rule_id': 'sustained_errors', 'name': 'Sustained Error Pattern',
            'description': 'Errors occurring consistently over time',
            'condition': 'trend.is_sustained and pattern.count > 20',
            'severity': AlertSeverity.MEDIUM, 'time_window_minutes': 120
        }
    
    def _create_new_pattern_rule(self) -> AlertRule:
        """Create new error pattern alert rule."""
        params = self._get_new_pattern_params()
        return self._build_alert_rule(**params)
    
    def _get_new_pattern_params(self) -> Dict:
        """Get parameters for new pattern rule."""
        return {
            'rule_id': 'new_error_pattern', 'name': 'New Error Pattern',
            'description': 'Previously unseen error pattern',
            'condition': 'pattern.count >= 5 and pattern_age_minutes < 30',
            'severity': AlertSeverity.MEDIUM, 'threshold_count': 5, 'time_window_minutes': 30
        }
    
    def _build_alert_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        condition: str,
        severity: AlertSeverity,
        time_window_minutes: int,
        threshold_count: Optional[int] = None
    ) -> AlertRule:
        """Build alert rule with parameters."""
        rule_params = self._prepare_rule_parameters(
            rule_id, name, description, condition, severity, threshold_count, time_window_minutes
        )
        return AlertRule(**rule_params)
    
    def _prepare_rule_parameters(
        self, rule_id: str, name: str, description: str, condition: str, 
        severity: AlertSeverity, threshold_count: Optional[int], time_window_minutes: int
    ) -> Dict:
        """Prepare parameters for AlertRule creation."""
        return {
            'rule_id': rule_id, 'name': name, 'description': description,
            'condition': condition, 'severity': severity,
            'threshold_count': threshold_count, 'time_window_minutes': time_window_minutes
        }
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add custom alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def evaluate_pattern(
        self,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend] = None
    ) -> List[ErrorAlert]:
        """Evaluate pattern against alert rules."""
        alerts = self._evaluate_rules_for_pattern(pattern, trend)
        self._store_alerts(alerts)
        return alerts
    
    def _store_alerts(self, alerts: List[ErrorAlert]) -> None:
        """Store alerts in internal list."""
        self.alerts.extend(alerts)
    
    def _evaluate_rules_for_pattern(
        self, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> List[ErrorAlert]:
        """Evaluate all rules for given pattern."""
        alerts = []
        self._check_rules_and_collect_alerts(alerts, pattern, trend)
        return alerts
    
    def _check_rules_and_collect_alerts(
        self, alerts: List[ErrorAlert], pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> None:
        """Check all rules and collect triggered alerts."""
        for rule in self.rules.values():
            alert = self._check_rule_for_alert(rule, pattern, trend)
            if alert:
                alerts.append(alert)
    
    def _check_rule_for_alert(
        self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> Optional[ErrorAlert]:
        """Check if rule should trigger alert."""
        if not self._should_evaluate_rule(rule):
            return None
        return self._process_rule_trigger(rule, pattern, trend)
    
    def _process_rule_trigger(
        self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> Optional[ErrorAlert]:
        """Process rule trigger and create alert."""
        if not self._evaluate_rule_condition(rule, pattern, trend):
            return None
        self._set_cooldown(rule.rule_id)
        return self._create_alert(rule, pattern, trend)
    
    def _should_evaluate_rule(self, rule: AlertRule) -> bool:
        """Check if rule should be evaluated."""
        return rule.active and not self._is_in_cooldown(rule.rule_id)
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.alert_history:
            return False
        return self._check_cooldown_period(rule_id)
    
    def _check_cooldown_period(self, rule_id: str) -> bool:
        """Check if rule is within cooldown period."""
        rule = self.rules[rule_id]
        last_alert = self.alert_history[rule_id]
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() - last_alert < cooldown_period
    
    def _set_cooldown(self, rule_id: str) -> None:
        """Set cooldown for rule."""
        self.alert_history[rule_id] = datetime.now()
    
    def _evaluate_rule_condition(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> bool:
        """Evaluate rule condition."""
        return self._safe_rule_evaluation(rule, pattern, trend)
    
    def _safe_rule_evaluation(self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]) -> bool:
        """Safely evaluate rule with error handling."""
        try:
            return self._execute_rule_evaluation(rule, pattern, trend)
        except Exception as e:
            return self._handle_rule_evaluation_error(rule, e)
    
    def _execute_rule_evaluation(
        self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> bool:
        """Execute rule evaluation with context."""
        context = self._build_evaluation_context(rule, pattern, trend)
        return eval(rule.condition, {'__builtins__': {}}, context)
    
    def _handle_rule_evaluation_error(self, rule: AlertRule, error: Exception) -> bool:
        """Handle rule evaluation error."""
        logger.error(f"Error evaluating rule {rule.rule_id}: {error}")
        return False
    
    def _build_evaluation_context(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> Dict:
        """Build context for rule evaluation."""
        pattern_age = self._calculate_pattern_age(pattern)
        return self._create_evaluation_dict(rule, pattern, trend, pattern_age)
    
    def _calculate_pattern_age(self, pattern: ErrorPattern) -> float:
        """Calculate pattern age in minutes."""
        return (datetime.now() - pattern.first_occurrence).total_seconds() / 60
    
    def _create_evaluation_dict(
        self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend], pattern_age: float
    ) -> Dict:
        """Create evaluation dictionary."""
        context_data = self._prepare_context_data(pattern, trend, rule.time_window_minutes, pattern_age)
        return context_data
    
    def _prepare_context_data(self, pattern: ErrorPattern, trend: Optional[ErrorTrend], window_minutes: int, pattern_age: float) -> Dict:
        """Prepare context data for evaluation."""
        return {
            'pattern': pattern, 'trend': trend,
            'window_minutes': window_minutes, 'pattern_age_minutes': pattern_age
        }
    
    def _create_alert(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> ErrorAlert:
        """Create alert from rule and pattern."""
        alert_components = self._prepare_alert_components(rule, pattern, trend)
        return self._build_error_alert(**alert_components)
    
    def _prepare_alert_components(self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]) -> Dict:
        """Prepare components for alert creation."""
        alert_id = self._generate_alert_id()
        message = self._generate_alert_message(rule, pattern, trend)
        return {'alert_id': alert_id, 'rule': rule, 'pattern': pattern, 'trend': trend, 'message': message}
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        return str(uuid.uuid4())
    
    def _build_error_alert(
        self, alert_id: str, rule: AlertRule, pattern: ErrorPattern, 
        trend: Optional[ErrorTrend], message: str
    ) -> ErrorAlert:
        """Build error alert instance."""
        alert_params = self._prepare_alert_parameters(alert_id, rule, pattern, trend, message)
        return ErrorAlert(**alert_params)
    
    def _prepare_alert_parameters(
        self, alert_id: str, rule: AlertRule, pattern: ErrorPattern, 
        trend: Optional[ErrorTrend], message: str
    ) -> Dict:
        """Prepare parameters for ErrorAlert creation."""
        return {
            'alert_id': alert_id, 'rule': rule, 'pattern': pattern,
            'trend': trend, 'message': message
        }
    
    def _generate_alert_message(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> str:
        """Generate alert message."""
        message_components = self._collect_message_components(rule, pattern, trend)
        return self._combine_message_parts(message_components['base_parts'], message_components['trend_parts'])
    
    def _collect_message_components(self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]) -> Dict:
        """Collect all message components."""
        base_parts = self._get_base_message_parts(rule, pattern)
        trend_parts = self._get_trend_message_parts(trend)
        return {'base_parts': base_parts, 'trend_parts': trend_parts}
    
    def _combine_message_parts(self, base_parts: List[str], trend_parts: List[str]) -> str:
        """Combine message parts into final message."""
        return " | ".join(base_parts + trend_parts)
    
    def _get_base_message_parts(
        self, 
        rule: AlertRule, 
        pattern: ErrorPattern
    ) -> List[str]:
        """Get base message parts."""
        return self._build_base_message_components(rule, pattern)
    
    def _build_base_message_components(self, rule: AlertRule, pattern: ErrorPattern) -> List[str]:
        """Build base message components."""
        return [
            f"Alert: {rule.name}",
            f"Error Pattern: {pattern.signature.error_type} in {pattern.signature.module}",
            f"Count: {pattern.count}",
            f"Affected Users: {len(pattern.affected_users)}"
        ]
    
    def _get_trend_message_parts(self, trend: Optional[ErrorTrend]) -> List[str]:
        """Get trend-specific message parts."""
        if not trend:
            return []
        return self._build_trend_components(trend)
    
    def _build_trend_components(self, trend: ErrorTrend) -> List[str]:
        """Build trend message components."""
        parts = []
        self._add_spike_info(parts, trend)
        self._add_sustained_info(parts, trend)
        self._add_projection_info(parts, trend)
        return parts
    
    def _add_spike_info(self, parts: List[str], trend: ErrorTrend) -> None:
        """Add spike information to parts."""
        if trend.is_spike:
            parts.append(" WARNING: [U+FE0F] Error spike detected")
    
    def _add_sustained_info(self, parts: List[str], trend: ErrorTrend) -> None:
        """Add sustained pattern information to parts."""
        if trend.is_sustained:
            parts.append("[U+1F4C8] Sustained error pattern")
    
    def _add_projection_info(self, parts: List[str], trend: ErrorTrend) -> None:
        """Add projection information to parts."""
        if trend.projection:
            parts.append(f"Projected: {trend.projection} errors next window")


class MetricsReporter:
    """Reports metrics and system status for error aggregation."""
    
    def __init__(self, aggregator, alert_engine) -> None:
        """Initialize metrics reporter."""
        self.aggregator = aggregator
        self.alert_engine = alert_engine
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status and metrics."""
        return self._build_status_dict()
    
    def _build_status_dict(self) -> Dict:
        """Build system status dictionary."""
        status_components = self._collect_status_components()
        return status_components
    
    def _collect_status_components(self) -> Dict:
        """Collect all status components."""
        return {
            'total_patterns': len(self.aggregator.patterns),
            'active_patterns': len(self.aggregator.get_patterns_in_window(60)),
            'total_alerts': len(self.alert_engine.alerts),
            'unresolved_alerts': self._count_unresolved_alerts(),
            'top_patterns': self._get_top_patterns_summary()
        }
    
    def _count_unresolved_alerts(self) -> int:
        """Count unresolved alerts."""
        return len([
            alert for alert in self.alert_engine.alerts
            if not alert.resolved
        ])
    
    def _get_top_patterns_summary(self) -> List[Dict]:
        """Get summary of top error patterns."""
        top_patterns = self.aggregator.get_top_patterns(5)
        return self._build_pattern_summaries(top_patterns)
    
    def _build_pattern_summaries(self, patterns) -> List[Dict]:
        """Build pattern summary dictionaries."""
        return [
            self._create_pattern_summary(pattern)
            for pattern in patterns
        ]
    
    def _create_pattern_summary(self, pattern) -> Dict:
        """Create individual pattern summary."""
        return {
            'signature': pattern.signature.pattern_hash,
            'count': pattern.count,
            'error_type': pattern.signature.error_type,
            'module': pattern.signature.module
        }