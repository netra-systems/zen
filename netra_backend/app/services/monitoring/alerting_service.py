"""Alerting Service for monitoring and notifications

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Proactive issue detection and resolution
- Value Impact: Prevents customer-impacting outages and reduces MTTR
- Strategic Impact: Maintains 99.9% uptime SLA and customer trust
"""

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class Alert:
    """Alert data model"""
    
    def __init__(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.alert_id = alert_id
        self.title = title
        self.description = description
        self.severity = severity
        self.source = source
        self.metadata = metadata or {}
        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.now(UTC)
        self.updated_at = self.created_at
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None


class AlertingService:
    """Service for managing alerts and notifications"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Any] = []
        self.suppression_rules: List[Dict[str, Any]] = []
        self.is_running = False
    
    async def start(self) -> None:
        """Start the alerting service"""
        self.is_running = True
        logger.info("Alerting service started")
    
    async def stop(self) -> None:
        """Stop the alerting service"""
        self.is_running = False
        logger.info("Alerting service stopped")
    
    async def create_alert(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert"""
        alert = Alert(alert_id, title, description, severity, source, metadata)
        self.alerts[alert_id] = alert
        
        # Process alert through handlers
        await self._process_alert(alert)
        
        logger.info(f"Alert created: {alert_id} - {title}")
        return alert
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        if alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(UTC)
            alert.updated_at = alert.acknowledged_at
            alert.metadata["acknowledged_by"] = acknowledged_by
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(UTC)
            alert.updated_at = alert.resolved_at
            alert.metadata["resolved_by"] = resolved_by
            
            logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            return True
        return False
    
    async def suppress_alert(self, alert_id: str, reason: str) -> bool:
        """Suppress an alert"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.SUPPRESSED
        alert.updated_at = datetime.now(UTC)
        alert.metadata["suppression_reason"] = reason
        
        logger.info(f"Alert suppressed: {alert_id} - {reason}")
        return True
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)
    
    async def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """List alerts with optional filtering"""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    async def add_alert_handler(self, handler) -> None:
        """Add alert handler"""
        self.alert_handlers.append(handler)
    
    async def remove_alert_handler(self, handler) -> None:
        """Remove alert handler"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
    
    async def add_suppression_rule(self, rule: Dict[str, Any]) -> None:
        """Add alert suppression rule"""
        self.suppression_rules.append(rule)
    
    async def _process_alert(self, alert: Alert) -> None:
        """Process alert through handlers and rules"""
        # Check suppression rules
        if await self._should_suppress_alert(alert):
            await self.suppress_alert(alert.alert_id, "Suppression rule matched")
            return
        
        # Process through handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    async def _should_suppress_alert(self, alert: Alert) -> bool:
        """Check if alert should be suppressed based on rules"""
        for rule in self.suppression_rules:
            if await self._matches_suppression_rule(alert, rule):
                return True
        return False
    
    async def _matches_suppression_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """Check if alert matches suppression rule"""
        # Simple rule matching - can be extended
        if "source" in rule and alert.source != rule["source"]:
            return False
        if "severity" in rule and alert.severity != AlertSeverity(rule["severity"]):
            return False
        if "pattern" in rule and rule["pattern"] not in alert.title:
            return False
        return True
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get alerting service metrics"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE])
        critical_alerts = len([a for a in self.alerts.values() if a.severity == AlertSeverity.CRITICAL])
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "handlers_count": len(self.alert_handlers),
            "suppression_rules_count": len(self.suppression_rules),
            "service_running": self.is_running
        }