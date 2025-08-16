"""Alert engine and metrics reporting for error aggregation.

Provides intelligent alerting based on error patterns and trends,
with configurable rules and cooldown mechanisms.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.core.error_aggregation_base import (
    AlertRule, AlertSeverity, ErrorAlert, ErrorPattern, ErrorTrend
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertEngine:
    """Generates alerts based on error patterns and trends."""
    
    def __init__(self):
        """Initialize alert engine."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[ErrorAlert] = []
        self.alert_history: Dict[str, datetime] = {}  # Rule cooldowns
        
        # Setup default alert rules
        self._setup_default_rules()
    
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
    
    def _create_sustained_errors_rule(self) -> AlertRule:
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
        alerts = []
        
        for rule in self.rules.values():
            if not self._should_evaluate_rule(rule):
                continue
            
            if self._evaluate_rule_condition(rule, pattern, trend):
                alert = self._create_alert(rule, pattern, trend)
                alerts.append(alert)
                self._set_cooldown(rule.rule_id)
        
        self.alerts.extend(alerts)
        return alerts
    
    def _should_evaluate_rule(self, rule: AlertRule) -> bool:
        """Check if rule should be evaluated."""
        return rule.active and not self._is_in_cooldown(rule.rule_id)
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.alert_history:
            return False
        
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
    ) -> Dict:
        """Build context for rule evaluation."""
        pattern_age = (datetime.now() - pattern.first_occurrence).total_seconds() / 60
        
        return {
            'pattern': pattern,
            'trend': trend,
            'window_minutes': rule.time_window_minutes,
            'pattern_age_minutes': pattern_age
        }
    
    def _create_alert(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> ErrorAlert:
        """Create alert from rule and pattern."""
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
        """Generate alert message."""
        base_parts = self._get_base_message_parts(rule, pattern)
        trend_parts = self._get_trend_message_parts(trend)
        
        return " | ".join(base_parts + trend_parts)
    
    def _get_base_message_parts(
        self, 
        rule: AlertRule, 
        pattern: ErrorPattern
    ) -> List[str]:
        """Get base message parts."""
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
        
        parts = []
        if trend.is_spike:
            parts.append("⚠️ Error spike detected")
        if trend.is_sustained:
            parts.append("📈 Sustained error pattern")
        if trend.projection:
            parts.append(f"Projected: {trend.projection} errors next window")
        
        return parts


class MetricsReporter:
    """Reports metrics and system status for error aggregation."""
    
    def __init__(self, aggregator, alert_engine):
        """Initialize metrics reporter."""
        self.aggregator = aggregator
        self.alert_engine = alert_engine
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status and metrics."""
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
        return [
            {
                'signature': pattern.signature.pattern_hash,
                'count': pattern.count,
                'error_type': pattern.signature.error_type,
                'module': pattern.signature.module
            }
            for pattern in self.aggregator.get_top_patterns(5)
        ]