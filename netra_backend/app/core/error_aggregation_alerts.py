"""Error alert management module - rule-based alerting system.

Provides comprehensive alert rule management, evaluation, and 
intelligent alerting for proactive error monitoring and response.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_aggregation_utils import (
    AlertRule,
    ErrorAlert,
    ErrorPattern,
    ErrorTrend,
)
from netra_backend.app.core.resilience.monitor import AlertSeverity
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertEngine:
    """Generates alerts based on error patterns and trends."""
    
    def __init__(self):
        """Initialize alert engine with default rules."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[ErrorAlert] = []
        self.alert_history: Dict[str, datetime] = {}  # Rule cooldowns
        self._setup_default_rules()
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add custom alert rule to engine."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def evaluate_pattern(
        self,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend] = None
    ) -> List[ErrorAlert]:
        """Evaluate pattern against all active alert rules."""
        alerts = self._process_rules_for_pattern(pattern, trend)
        self.alerts.extend(alerts)
        return alerts
    
    def _process_rules_for_pattern(
        self, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> List[ErrorAlert]:
        """Process all rules for given pattern."""
        alerts = []
        for rule in self._get_active_rules():
            alert = self._check_rule_against_pattern(rule, pattern, trend)
            if alert:
                alerts.append(alert)
        return alerts
    
    def _check_rule_against_pattern(
        self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]
    ) -> Optional[ErrorAlert]:
        """Check single rule against pattern."""
        if not self._should_evaluate_rule(rule):
            return None
        alert = self._evaluate_single_rule(rule, pattern, trend)
        if alert:
            self._set_rule_cooldown(rule.rule_id)
        return alert
    
    def _setup_default_rules(self) -> None:
        """Setup comprehensive default alert rules."""
        self.rules = {
            'high_error_rate': self._create_high_error_rate_rule(),
            'critical_error_spike': self._create_critical_spike_rule(),
            'sustained_errors': self._create_sustained_error_rule(),
            'new_error_pattern': self._create_new_pattern_rule()
        }
    
    def _create_high_error_rate_rule(self) -> AlertRule:
        """Create high error rate alert rule."""
        config = self._get_high_error_rate_config()
        return AlertRule(**config)

    def _get_high_error_rate_config(self) -> Dict[str, Any]:
        """Get configuration for high error rate rule."""
        return {
            'rule_id': 'high_error_rate',
            'name': 'High Error Rate',
            'description': 'Error rate exceeds threshold',
            'condition': 'pattern.count > 50 and window_minutes <= 60',
            'severity': AlertSeverity.HIGH,
            'threshold_count': 50,
            'time_window_minutes': 60
        }
    
    def _create_critical_spike_rule(self) -> AlertRule:
        """Create critical error spike alert rule."""
        config = self._get_critical_spike_config()
        return AlertRule(**config)

    def _get_critical_spike_config(self) -> Dict[str, Any]:
        """Get configuration for critical spike rule."""
        return {
            'rule_id': 'critical_error_spike',
            'name': 'Critical Error Spike',
            'description': 'Sudden spike in critical errors',
            'condition': 'trend.is_spike and pattern.severity_distribution.get("critical", 0) > 0',
            'severity': AlertSeverity.CRITICAL,
            'time_window_minutes': 30
        }
    
    def _create_sustained_error_rule(self) -> AlertRule:
        """Create sustained error pattern alert rule."""
        config = self._get_sustained_error_config()
        return AlertRule(**config)

    def _get_sustained_error_config(self) -> Dict[str, Any]:
        """Get configuration for sustained error rule."""
        return {
            'rule_id': 'sustained_errors',
            'name': 'Sustained Error Pattern',
            'description': 'Errors occurring consistently over time',
            'condition': 'trend.is_sustained and pattern.count > 20',
            'severity': AlertSeverity.MEDIUM,
            'time_window_minutes': 120
        }
    
    def _create_new_pattern_rule(self) -> AlertRule:
        """Create new error pattern alert rule."""
        config = self._get_new_pattern_config()
        return AlertRule(**config)

    def _get_new_pattern_config(self) -> Dict[str, Any]:
        """Get configuration for new pattern rule."""
        return {
            'rule_id': 'new_error_pattern',
            'name': 'New Error Pattern',
            'description': 'Previously unseen error pattern',
            'condition': 'pattern.count >= 5 and pattern_age_minutes < 30',
            'severity': AlertSeverity.MEDIUM,
            'threshold_count': 5,
            'time_window_minutes': 30
        }
    
    def _get_active_rules(self) -> List[AlertRule]:
        """Get all active alert rules."""
        return [rule for rule in self.rules.values() if rule.active]
    
    def _should_evaluate_rule(self, rule: AlertRule) -> bool:
        """Check if rule should be evaluated (not in cooldown)."""
        return not self._is_in_cooldown(rule.rule_id)
    
    def _evaluate_single_rule(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> Optional[ErrorAlert]:
        """Evaluate single rule against pattern and trend."""
        if self._evaluate_rule_condition(rule, pattern, trend):
            return self._create_alert(rule, pattern, trend)
        return None
    
    def _set_rule_cooldown(self, rule_id: str) -> None:
        """Set cooldown timestamp for rule."""
        self.alert_history[rule_id] = datetime.now()
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.alert_history:
            return False
        return self._check_cooldown_period(rule_id)
    
    def _check_cooldown_period(self, rule_id: str) -> bool:
        """Check if cooldown period is still active."""
        rule = self.rules[rule_id]
        last_alert = self.alert_history[rule_id]
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() - last_alert < cooldown_period
    
    def _evaluate_rule_condition(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> bool:
        """Evaluate rule condition with proper context."""
        return self._safe_evaluate_condition(rule, pattern, trend)

    def _safe_evaluate_condition(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> bool:
        """Safely evaluate rule condition with error handling."""
        return self._execute_condition_evaluation(rule, pattern, trend)
    
    def _execute_condition_evaluation(self, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend]) -> bool:
        """Execute condition evaluation with error handling."""
        try:
            context = self._build_evaluation_context(rule, pattern, trend)
            return eval(rule.condition, {'__builtins__': {}}, context)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return False
    
    def _build_evaluation_context(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> Dict[str, Any]:
        """Build context dictionary for rule evaluation."""
        return self._create_context_dict(rule, pattern, trend)

    def _create_context_dict(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> Dict[str, Any]:
        """Create context dictionary with all evaluation variables."""
        return {
            'pattern': pattern,
            'trend': trend,
            'window_minutes': rule.time_window_minutes,
            'pattern_age_minutes': self._calculate_pattern_age(pattern)
        }
    
    def _calculate_pattern_age(self, pattern: ErrorPattern) -> float:
        """Calculate pattern age in minutes."""
        return (datetime.now() - pattern.first_occurrence).total_seconds() / 60
    
    def _create_alert(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> ErrorAlert:
        """Create alert from rule and pattern data."""
        alert_id = self._generate_alert_id()
        message = self._generate_alert_message(rule, pattern, trend)
        return self._build_error_alert(alert_id, rule, pattern, trend, message)

    def _generate_alert_id(self) -> str:
        """Generate unique alert identifier."""
        return str(uuid.uuid4())

    def _build_error_alert(
        self,
        alert_id: str,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend],
        message: str
    ) -> ErrorAlert:
        """Build ErrorAlert object with provided components."""
        alert_params = self._prepare_alert_params(alert_id, rule, pattern, trend, message)
        return ErrorAlert(**alert_params)
    
    def _prepare_alert_params(self, alert_id: str, rule: AlertRule, pattern: ErrorPattern, trend: Optional[ErrorTrend], message: str) -> Dict[str, Any]:
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
        """Generate comprehensive alert message."""
        return self._combine_message_parts(rule, pattern, trend)

    def _combine_message_parts(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> str:
        """Combine base and trend message parts into final message."""
        base_parts = self._build_base_message_parts(rule, pattern)
        trend_parts = self._build_trend_message_parts(trend)
        return " | ".join(base_parts + trend_parts)
    
    def _build_base_message_parts(self, rule: AlertRule, pattern: ErrorPattern) -> List[str]:
        """Build base message components."""
        return [
            f"Alert: {rule.name}",
            f"Error Pattern: {pattern.signature.error_type} in {pattern.signature.module}",
            f"Count: {pattern.count}",
            f"Affected Users: {len(pattern.affected_users)}"
        ]
    
    def _build_trend_message_parts(self, trend: Optional[ErrorTrend]) -> List[str]:
        """Build trend-specific message components."""
        if not trend:
            return []
        return self._collect_trend_indicators(trend)

    def _collect_trend_indicators(self, trend: ErrorTrend) -> List[str]:
        """Collect all trend indicator messages."""
        parts = []
        parts.extend(self._get_spike_indicators(trend))
        parts.extend(self._get_sustained_indicators(trend))
        parts.extend(self._get_projection_indicators(trend))
        return parts

    def _get_spike_indicators(self, trend: ErrorTrend) -> List[str]:
        """Get spike indicator messages."""
        return [" WARNING: [U+FE0F] Error spike detected"] if trend.is_spike else []

    def _get_sustained_indicators(self, trend: ErrorTrend) -> List[str]:
        """Get sustained pattern indicator messages."""
        return ["[U+1F4C8] Sustained error pattern"] if trend.is_sustained else []

    def _get_projection_indicators(self, trend: ErrorTrend) -> List[str]:
        """Get projection indicator messages."""
        if trend.projection:
            return [f"Projected: {trend.projection} errors next window"]
        return []