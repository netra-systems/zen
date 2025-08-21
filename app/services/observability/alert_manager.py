"""Alert Manager Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic alert management functionality for tests
- Value Impact: Ensures alert management tests can execute without import errors
- Strategic Impact: Enables alerting functionality validation
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    query: str  # Metric query or condition
    threshold: float
    severity: AlertSeverity = AlertSeverity.MEDIUM
    duration: timedelta = timedelta(minutes=5)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.PENDING
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    value: Optional[float] = None
    alert_id: str = field(default_factory=lambda: str(id(object())))


class AlertManager:
    """Manages alerts and alert rules."""
    
    def __init__(self):
        """Initialize alert manager."""
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._notification_handlers: List[Callable] = []
        self._silenced_alerts: Set[str] = set()
        self._lock = asyncio.Lock()
        self._evaluation_task: Optional[asyncio.Task] = None
        self._running = False
        self._evaluation_interval = 30  # seconds
    
    async def start(self) -> None:
        """Start the alert manager."""
        self._running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
    
    async def stop(self) -> None:
        """Stop the alert manager."""
        self._running = False
        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
    
    async def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        async with self._lock:
            self._rules[rule.name] = rule
    
    async def remove_rule(self, rule_name: str) -> None:
        """Remove an alert rule."""
        async with self._lock:
            self._rules.pop(rule_name, None)
            # Also remove any active alerts for this rule
            to_remove = [alert_id for alert_id, alert in self._alerts.items() 
                        if alert.rule_name == rule_name]
            for alert_id in to_remove:
                del self._alerts[alert_id]
    
    async def fire_alert(
        self, 
        rule_name: str, 
        value: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> str:
        """Fire an alert manually."""
        async with self._lock:
            rule = self._rules.get(rule_name)
            if not rule:
                raise ValueError(f"Alert rule '{rule_name}' not found")
            
            alert = Alert(
                rule_name=rule_name,
                severity=rule.severity,
                status=AlertStatus.FIRING,
                labels={**rule.labels, **(labels or {})},
                annotations={**rule.annotations, **(annotations or {})},
                value=value
            )
            
            self._alerts[alert.alert_id] = alert
            await self._notify_handlers(alert)
            return alert.alert_id
    
    async def resolve_alert(self, alert_id: str) -> None:
        """Resolve an alert."""
        async with self._lock:
            if alert_id in self._alerts:
                alert = self._alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.end_time = datetime.now()
                await self._notify_handlers(alert)
    
    async def silence_alert(self, alert_id: str, duration: Optional[timedelta] = None) -> None:
        """Silence an alert."""
        async with self._lock:
            if alert_id in self._alerts:
                self._silenced_alerts.add(alert_id)
                alert = self._alerts[alert_id]
                alert.status = AlertStatus.SILENCED
                
                # Auto-unsilence after duration
                if duration:
                    asyncio.create_task(self._auto_unsilence(alert_id, duration))
    
    async def get_alerts(
        self, 
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alerts filtered by status and/or severity."""
        async with self._lock:
            alerts = list(self._alerts.values())
            
            if status:
                alerts = [a for a in alerts if a.status == status]
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            return alerts
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of all alerts."""
        async with self._lock:
            status_counts = {}
            severity_counts = {}
            
            for alert in self._alerts.values():
                status_counts[alert.status.value] = status_counts.get(alert.status.value, 0) + 1
                severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
            
            return {
                "total_alerts": len(self._alerts),
                "total_rules": len(self._rules),
                "silenced_count": len(self._silenced_alerts),
                "status_breakdown": status_counts,
                "severity_breakdown": severity_counts,
                "evaluation_interval": self._evaluation_interval
            }
    
    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a notification handler for alerts."""
        self._notification_handlers.append(handler)
    
    async def clear_alerts(self) -> None:
        """Clear all alerts."""
        async with self._lock:
            self._alerts.clear()
            self._silenced_alerts.clear()
    
    async def _evaluation_loop(self) -> None:
        """Background loop for evaluating alert rules."""
        while self._running:
            try:
                await self._evaluate_rules()
                await asyncio.sleep(self._evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue evaluation
                await asyncio.sleep(1)
    
    async def _evaluate_rules(self) -> None:
        """Evaluate all alert rules."""
        # In a real implementation, this would query metrics and evaluate conditions
        # For testing, we just maintain the alert state
        pass
    
    async def _notify_handlers(self, alert: Alert) -> None:
        """Notify all registered handlers about an alert."""
        for handler in self._notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                # Log error but continue with other handlers
                pass
    
    async def _auto_unsilence(self, alert_id: str, duration: timedelta) -> None:
        """Auto-unsilence an alert after duration."""
        await asyncio.sleep(duration.total_seconds())
        async with self._lock:
            self._silenced_alerts.discard(alert_id)
            if alert_id in self._alerts:
                alert = self._alerts[alert_id]
                if alert.status == AlertStatus.SILENCED:
                    alert.status = AlertStatus.FIRING


# Global alert manager instance
default_alert_manager = AlertManager()