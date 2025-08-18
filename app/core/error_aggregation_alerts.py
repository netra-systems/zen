"""Error alert management module - rule-based alerting system.

Provides comprehensive alert rule management, evaluation, and 
intelligent alerting for proactive error monitoring and response.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.logging_config import central_logger
from .error_aggregation_utils import (
    ErrorPattern, ErrorTrend, AlertRule, ErrorAlert, AlertSeverity
)

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
        return AlertRule(
            rule_id='high_error_rate',
            name='High Error Rate',
            description='Error rate exceeds threshold',
            condition='pattern.count > 50 and window_minutes <= 60',
            severity=AlertSeverity.HIGH,
            threshold_count=50,
            time_window_minutes=60
        )
    
    def _create_critical_spike_rule(self) -> AlertRule:
        """Create critical error spike alert rule."""
        return AlertRule(
            rule_id='critical_error_spike',
            name='Critical Error Spike',
            description='Sudden spike in critical errors',
            condition='trend.is_spike and pattern.severity_distribution.get("critical", 0) > 0',
            severity=AlertSeverity.CRITICAL,
            time_window_minutes=30
        )
    
    def _create_sustained_error_rule(self) -> AlertRule:
        """Create sustained error pattern alert rule."""
        return AlertRule(
            rule_id='sustained_errors',
            name='Sustained Error Pattern',
            description='Errors occurring consistently over time',
            condition='trend.is_sustained and pattern.count > 20',
            severity=AlertSeverity.MEDIUM,
            time_window_minutes=120
        )
    
    def _create_new_pattern_rule(self) -> AlertRule:
        """Create new error pattern alert rule."""
        return AlertRule(
            rule_id='new_error_pattern',
            name='New Error Pattern',
            description='Previously unseen error pattern',
            condition='pattern.count >= 5 and pattern_age_minutes < 30',
            severity=AlertSeverity.MEDIUM,
            threshold_count=5,
            time_window_minutes=30
        )
    
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
        alert_id = str(uuid.uuid4())
        message = self._generate_alert_message(rule, pattern, trend)
        return ErrorAlert(
            alert_id=alert_id,
            rule=rule,
            pattern=pattern,
            trend=trend,
            message=message
        )
    
    def _generate_alert_message(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> str:
        """Generate comprehensive alert message."""
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
        parts = []
        if trend.is_spike:
            parts.append("⚠️ Error spike detected")
        if trend.is_sustained:
            parts.append("📈 Sustained error pattern")
        if trend.projection:
            parts.append(f"Projected: {trend.projection} errors next window")
        return parts