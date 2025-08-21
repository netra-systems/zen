"""Alert management for quality monitoring"""

from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from collections import deque
import statistics

from netra_backend.app.logging_config import central_logger
from netra_backend.app.models import AlertSeverity, MetricType, QualityAlert
from netra_backend.app.services.quality_gate_service import QualityMetrics

logger = central_logger.get_logger(__name__)


class QualityAlertManager:
    """Manages quality alerts and thresholds"""
    
    ALERT_THRESHOLDS = {
        MetricType.QUALITY_SCORE: {
            AlertSeverity.WARNING: 0.5,
            AlertSeverity.ERROR: 0.4,
            AlertSeverity.CRITICAL: 0.3
        },
        MetricType.SLOP_DETECTION_RATE: {
            AlertSeverity.WARNING: 0.1,
            AlertSeverity.ERROR: 0.2,
            AlertSeverity.CRITICAL: 0.3
        },
        MetricType.RETRY_RATE: {
            AlertSeverity.WARNING: 0.15,
            AlertSeverity.ERROR: 0.25,
            AlertSeverity.CRITICAL: 0.4
        },
        MetricType.FALLBACK_RATE: {
            AlertSeverity.WARNING: 0.1,
            AlertSeverity.ERROR: 0.2,
            AlertSeverity.CRITICAL: 0.3
        },
        MetricType.ERROR_RATE: {
            AlertSeverity.WARNING: 0.05,
            AlertSeverity.ERROR: 0.1,
            AlertSeverity.CRITICAL: 0.2
        }
    }
    
    def __init__(self):
        self.alert_history = deque(maxlen=500)
        self.active_alerts: Dict[str, QualityAlert] = {}
    
    async def check_thresholds(self, metrics_buffer: Dict) -> List[QualityAlert]:
        """Check metrics against thresholds"""
        new_alerts = []
        for agent_name, events in metrics_buffer.items():
            if not events:
                continue
            alerts = self._check_agent_thresholds(agent_name, list(events)[-20:])
            new_alerts.extend(alerts)
        self._store_alerts(new_alerts)
        return new_alerts
    
    def _check_agent_thresholds(self, agent: str, events: List) -> List[QualityAlert]:
        """Check thresholds for single agent"""
        alerts = []
        avg_quality = statistics.mean([e['quality_score'] for e in events])
        alert = self._check_quality_score(agent, avg_quality)
        if alert:
            alerts.append(alert)
        alert = self._check_slop_rate(agent, events)
        if alert:
            alerts.append(alert)
        alert = self._check_circular_reasoning(agent, events)
        if alert:
            alerts.append(alert)
        return alerts
    
    def _check_quality_score(self, agent: str, score: float) -> Optional[QualityAlert]:
        """Check quality score threshold"""
        return self._create_alert_if_needed(
            MetricType.QUALITY_SCORE, score, agent,
            f"Average quality score {score:.2f} for {agent}"
        )
    
    def _check_slop_rate(self, agent: str, events: List) -> Optional[QualityAlert]:
        """Check slop detection rate"""
        slop = sum(1 for e in events if e['quality_level'] in ['poor', 'unacceptable'])
        rate = slop / len(events) if events else 0
        return self._create_alert_if_needed(
            MetricType.SLOP_DETECTION_RATE, rate, agent,
            f"Slop detection rate {rate:.1%} for {agent}"
        )
    
    def _check_circular_reasoning(self, agent: str, events: List) -> Optional[QualityAlert]:
        """Check for circular reasoning pattern"""
        count = sum(1 for e in events if e.get('circular_reasoning', False))
        if count > 3:
            return QualityAlert(
                id=f"circular_{agent}_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC),
                severity=AlertSeverity.WARNING,
                metric_type=MetricType.QUALITY_SCORE,
                agent=agent,
                message=f"Repeated circular reasoning in {agent}",
                current_value=count,
                threshold=3,
                details={'recent_count': count}
            )
        return None
    
    def _create_alert_if_needed(
        self, metric_type: MetricType, value: float,
        agent: str, message: str
    ) -> Optional[QualityAlert]:
        """Create alert if threshold exceeded"""
        if metric_type not in self.ALERT_THRESHOLDS:
            return None
        thresholds = self.ALERT_THRESHOLDS[metric_type]
        for severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR, AlertSeverity.WARNING]:
            if severity not in thresholds:
                continue
            threshold = thresholds[severity]
            if self._is_threshold_exceeded(metric_type, value, threshold):
                return self._create_alert(
                    metric_type, severity, agent, message, value, threshold
                )
        return None
    
    def _is_threshold_exceeded(self, metric: MetricType, value: float, threshold: float) -> bool:
        """Check if threshold is exceeded"""
        if metric == MetricType.QUALITY_SCORE:
            return value < threshold
        return value > threshold
    
    def _create_alert(
        self, metric: MetricType, severity: AlertSeverity,
        agent: str, message: str, value: float, threshold: float
    ) -> QualityAlert:
        """Create new alert"""
        return QualityAlert(
            id=f"{metric.value}_{agent}_{datetime.now(UTC).timestamp()}",
            timestamp=datetime.now(UTC),
            severity=severity,
            metric_type=metric,
            agent=agent,
            message=message,
            current_value=value,
            threshold=threshold
        )
    
    def _store_alerts(self, alerts: List[QualityAlert]):
        """Store new alerts"""
        for alert in alerts:
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
    
    async def check_immediate_alert(self, agent: str, metrics: QualityMetrics):
        """Check for immediate alert conditions"""
        if metrics.overall_score < 0.3:
            alert = QualityAlert(
                id=f"critical_{agent}_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC),
                severity=AlertSeverity.CRITICAL,
                metric_type=MetricType.QUALITY_SCORE,
                agent=agent,
                message=f"Critical quality failure in {agent}: {metrics.overall_score:.2f}",
                current_value=metrics.overall_score,
                threshold=0.3,
                details={'issues': metrics.issues}
            )
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            await self._broadcast_critical(alert)
    
    async def _broadcast_critical(self, alert: QualityAlert):
        """Broadcast critical alert"""
        logger.critical(f"CRITICAL ALERT: {alert.message}")
    
    async def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        return False
    
    async def resolve(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False
    
    def get_active_alerts(self) -> List[QualityAlert]:
        """Get all active alerts"""
        return [a for a in self.active_alerts.values() if not a.resolved]
    
    def get_recent_alerts(self, limit: int = 10) -> List[QualityAlert]:
        """Get recent alerts"""
        return list(self.alert_history)[-limit:]