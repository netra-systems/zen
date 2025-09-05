"""Quality Monitoring Alert System

Manages quality alerts for agent performance and system metrics.
Provides threshold-based alerting for SLA compliance.
"""

from datetime import datetime
from typing import Dict, List, Optional

from netra_backend.app.core.health_types import AlertSeverity
from netra_backend.app.services.quality_monitoring.models import (
    QualityAlert,
    MetricType
)


class QualityAlertManager:
    """Manages quality alerts for monitoring system.
    
    Tracks performance degradations and SLA violations to protect
    revenue and maintain service quality.
    """
    
    def __init__(self):
        self.alerts: List[QualityAlert] = []
        self.thresholds = {
            'response_time': 2000,  # ms
            'error_rate': 0.01,  # 1%
            'availability': 99.9,  # percentage
        }
    
    def create_alert(
        self, 
        agent: str,
        metric_type: MetricType,
        message: str,
        current_value: float,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.INFO,
        details: Optional[Dict] = None
    ) -> QualityAlert:
        """Create a new quality alert.
        
        Args:
            agent: Agent name
            metric_type: Type of metric that triggered alert
            message: Alert message 
            current_value: Current metric value
            threshold: Threshold value
            severity: Alert severity level
            details: Additional alert details
            
        Returns:
            Created quality alert
        """
        alert = QualityAlert(
            id=f"alert_{len(self.alerts)}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            severity=severity,
            metric_type=metric_type,
            agent=agent,
            message=message,
            current_value=current_value,
            threshold=threshold,
            details=details or {}
        )
        self.alerts.append(alert)
        return alert
    
    def check_thresholds(self, metrics: Dict) -> List[QualityAlert]:
        """Check metrics against thresholds and create alerts.
        
        Args:
            metrics: Current system metrics
            
        Returns:
            List of alerts created for threshold violations
        """
        alerts = []
        
        # Check response time
        if 'response_time' in metrics and 'agent' in metrics:
            if metrics['response_time'] > self.thresholds['response_time']:
                alert = self.create_alert(
                    agent=metrics.get('agent', 'system'),
                    metric_type=MetricType.RESPONSE_TIME,
                    message=f"Response time {metrics['response_time']}ms exceeds threshold {self.thresholds['response_time']}ms",
                    current_value=metrics['response_time'],
                    threshold=self.thresholds['response_time'],
                    severity=AlertSeverity.WARNING
                )
                alerts.append(alert)
        
        # Check error rate
        if 'error_rate' in metrics and 'agent' in metrics:
            if metrics['error_rate'] > self.thresholds['error_rate']:
                alert = self.create_alert(
                    agent=metrics.get('agent', 'system'),
                    metric_type=MetricType.ERROR_RATE,
                    message=f"Error rate {metrics['error_rate']*100:.2f}% exceeds threshold {self.thresholds['error_rate']*100:.2f}%",
                    current_value=metrics['error_rate'],
                    threshold=self.thresholds['error_rate'],
                    severity=AlertSeverity.ERROR
                )
                alerts.append(alert)
        
        # Check availability
        if 'availability' in metrics and 'agent' in metrics:
            if metrics['availability'] < self.thresholds['availability']:
                alert = self.create_alert(
                    agent=metrics.get('agent', 'system'),
                    metric_type=MetricType.ERROR_RATE,
                    message=f"Availability {metrics['availability']:.2f}% below SLA target {self.thresholds['availability']}%",
                    current_value=metrics['availability'],
                    threshold=self.thresholds['availability'],
                    severity=AlertSeverity.CRITICAL
                )
                alerts.append(alert)
        
        return alerts
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[QualityAlert]:
        """Get active alerts, optionally filtered by severity.
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        if severity:
            return [a for a in self.alerts if a.severity == severity]
        return self.alerts.copy()
    
    def clear_alerts(self, older_than: Optional[datetime] = None):
        """Clear alerts older than specified time.
        
        Args:
            older_than: Clear alerts older than this timestamp
        """
        if older_than:
            self.alerts = [a for a in self.alerts if a.timestamp > older_than]
        else:
            self.alerts.clear()