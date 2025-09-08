"""
JWT Secret Drift Detection and Monitoring

This module provides continuous monitoring of JWT secret consistency across services,
with automatic detection of configuration drift that could cause authentication failures.

Business Value:
- Prevents $50K MRR loss from undetected JWT secret misconfigurations
- Enables proactive detection of environment variable drift
- Provides automated alerting for JWT secret inconsistencies
- Supports zero-downtime JWT secret rotation with validation

CRITICAL: This monitor should be integrated into:
- Production health checks
- Staging deployment validation
- Development environment startup
- JWT secret rotation workflows
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from shared.isolated_environment import get_env
from shared.jwt_secret_consistency_validator import (
    get_jwt_consistency_validator,
    ConsistencyValidationReport,
    ValidationResult
)

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """JWT secret drift alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class JWTDriftAlert:
    """JWT secret drift alert."""
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    service_name: str
    issue: str
    impact: str
    remediation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Configuration for JWT secret drift monitoring."""
    check_interval_seconds: int = 300  # Check every 5 minutes
    alert_threshold_seconds: int = 60  # Alert if inconsistency lasts > 1 minute
    max_consecutive_failures: int = 3  # Max consecutive validation failures
    enable_alerting: bool = True
    enable_auto_remediation: bool = False  # Future feature
    services_to_monitor: List[str] = field(default_factory=lambda: [
        "unified_manager", "auth_service", "backend_service", "test_framework"
    ])


class JWTSecretDriftMonitor:
    """
    Monitors JWT secret consistency across services and detects configuration drift.
    
    This monitor runs continuously and validates that all services maintain
    consistent JWT secret configuration, alerting on any drift that could
    cause authentication failures.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """Initialize JWT secret drift monitor."""
        self.config = config or MonitoringConfig()
        self.env = get_env()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_validation: Optional[ConsistencyValidationReport] = None
        self.consecutive_failures = 0
        self.drift_start_time: Optional[datetime] = None
        
        # Alert system
        self.alert_handlers: List[Callable[[JWTDriftAlert], None]] = []
        self.alert_history: List[JWTDriftAlert] = []
        
        # Performance tracking
        self.validation_count = 0
        self.total_validation_time = 0.0
        self.last_validation_time: Optional[datetime] = None
        
        # Get validator instance
        self.validator = get_jwt_consistency_validator()
        
        logger.info("JWT Secret Drift Monitor initialized")
        logger.info(f"  Check interval: {self.config.check_interval_seconds}s")
        logger.info(f"  Alert threshold: {self.config.alert_threshold_seconds}s")
        logger.info(f"  Services monitored: {', '.join(self.config.services_to_monitor)}")
    
    def add_alert_handler(self, handler: Callable[[JWTDriftAlert], None]) -> None:
        """Add alert handler for JWT drift notifications."""
        self.alert_handlers.append(handler)
        logger.info(f"Added JWT drift alert handler: {handler.__name__}")
    
    def _create_alert(
        self,
        level: AlertLevel,
        service_name: str,
        issue: str,
        impact: str,
        remediation: str,
        **metadata
    ) -> JWTDriftAlert:
        """Create JWT drift alert."""
        alert_id = f"jwt_drift_{int(time.time())}_{hash(issue) & 0xFFFF:04x}"
        
        alert = JWTDriftAlert(
            alert_id=alert_id,
            timestamp=datetime.now(timezone.utc),
            level=level,
            service_name=service_name,
            issue=issue,
            impact=impact,
            remediation=remediation,
            metadata=metadata
        )
        
        # Store in history
        self.alert_history.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
            
        return alert
    
    def _send_alert(self, alert: JWTDriftAlert) -> None:
        """Send alert to all configured handlers."""
        if not self.config.enable_alerting:
            return
            
        logger.log(
            logging.CRITICAL if alert.level == AlertLevel.EMERGENCY else
            logging.ERROR if alert.level == AlertLevel.CRITICAL else
            logging.WARNING if alert.level == AlertLevel.WARNING else
            logging.INFO,
            f"🚨 JWT DRIFT ALERT [{alert.level.value.upper()}]: {alert.issue}"
        )
        logger.log(
            logging.ERROR if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] else logging.WARNING,
            f"   Service: {alert.service_name}"
        )
        logger.log(
            logging.ERROR if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] else logging.WARNING,
            f"   Impact: {alert.impact}"
        )
        logger.log(
            logging.ERROR if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] else logging.WARNING,
            f"   Remediation: {alert.remediation}"
        )
        
        # Send to all handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler {handler.__name__} failed: {e}")
    
    async def _perform_validation(self) -> ConsistencyValidationReport:
        """Perform JWT secret consistency validation."""
        start_time = time.time()
        
        try:
            report = await self.validator.validate_cross_service_consistency()
            
            # Update performance tracking
            validation_time = time.time() - start_time
            self.validation_count += 1
            self.total_validation_time += validation_time
            self.last_validation_time = datetime.now(timezone.utc)
            
            logger.debug(f"JWT validation completed in {validation_time:.3f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"JWT validation failed: {e}")
            
            # Create error report
            from shared.jwt_secret_consistency_validator import (
                ConsistencyValidationReport, ValidationResult, ServiceJWTInfo
            )
            
            return ConsistencyValidationReport(
                validation_timestamp=datetime.now(timezone.utc),
                overall_result=ValidationResult.ERROR,
                services=[],
                inconsistencies=[f"Validation system error: {e}"],
                recommendations=["Check JWT validation system health"],
                summary=f"Validation failed: {e}"
            )
    
    def _analyze_drift(self, report: ConsistencyValidationReport) -> List[JWTDriftAlert]:
        """Analyze validation report for JWT secret drift."""
        alerts = []
        
        if report.overall_result == ValidationResult.INCONSISTENT:
            # JWT secrets are inconsistent across services
            if self.drift_start_time is None:
                self.drift_start_time = report.validation_timestamp
                
            # Check if drift has persisted long enough to alert
            drift_duration = (report.validation_timestamp - self.drift_start_time).total_seconds()
            
            if drift_duration > self.config.alert_threshold_seconds:
                # Determine alert level based on services affected
                reachable_services = [s for s in report.services if s.reachable]
                affected_count = len(set(s.jwt_secret_hash for s in reachable_services))
                
                if affected_count > 2:
                    level = AlertLevel.EMERGENCY
                    impact = f"CRITICAL: JWT authentication will fail for {len(reachable_services)} services"
                elif "auth_service" in [s.service_name for s in reachable_services]:
                    level = AlertLevel.CRITICAL
                    impact = "Auth service has different JWT secret - WebSocket auth will fail"
                else:
                    level = AlertLevel.WARNING
                    impact = f"JWT secret inconsistency across {len(reachable_services)} services"
                
                alert = self._create_alert(
                    level=level,
                    service_name="multiple",
                    issue=f"JWT secret drift detected for {drift_duration:.0f}s",
                    impact=impact,
                    remediation="Use unified JWT secret manager across all services",
                    drift_duration=drift_duration,
                    affected_services=[s.service_name for s in reachable_services],
                    secret_hashes=[s.jwt_secret_hash[:8] for s in reachable_services]
                )
                alerts.append(alert)
                
        elif report.overall_result == ValidationResult.CONSISTENT:
            # Reset drift tracking on successful validation
            if self.drift_start_time is not None:
                drift_duration = (report.validation_timestamp - self.drift_start_time).total_seconds()
                alert = self._create_alert(
                    level=AlertLevel.INFO,
                    service_name="all",
                    issue=f"JWT secret consistency restored after {drift_duration:.0f}s drift",
                    impact="WebSocket authentication now working correctly",
                    remediation="Monitor for future drift occurrences",
                    drift_duration=drift_duration
                )
                alerts.append(alert)
                
            self.drift_start_time = None
            self.consecutive_failures = 0
            
        elif report.overall_result == ValidationResult.ERROR:
            # Validation system error
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.config.max_consecutive_failures:
                alert = self._create_alert(
                    level=AlertLevel.CRITICAL,
                    service_name="monitor",
                    issue=f"JWT validation system failing ({self.consecutive_failures} consecutive failures)",
                    impact="Cannot detect JWT secret drift - authentication issues may go unnoticed",
                    remediation="Check JWT validation system and service availability",
                    consecutive_failures=self.consecutive_failures
                )
                alerts.append(alert)
                
        # Check for individual service issues
        for service in report.services:
            if not service.reachable and service.service_name in self.config.services_to_monitor:
                alert = self._create_alert(
                    level=AlertLevel.WARNING,
                    service_name=service.service_name,
                    issue=f"Service {service.service_name} unreachable for JWT validation",
                    impact=f"Cannot validate JWT secret for {service.service_name}",
                    remediation=f"Check {service.service_name} health and availability",
                    service_error=service.error
                )
                alerts.append(alert)
        
        return alerts
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("🔄 JWT Secret Drift Monitor started")
        
        while self.is_monitoring:
            try:
                # Perform validation
                report = await self._perform_validation()
                self.last_validation = report
                
                # Analyze for drift and create alerts
                alerts = self._analyze_drift(report)
                
                # Send alerts
                for alert in alerts:
                    self._send_alert(alert)
                
                # Log validation summary
                if report.overall_result == ValidationResult.CONSISTENT:
                    logger.debug(f"✅ JWT consistency validated across {len(report.services)} services")
                elif report.overall_result == ValidationResult.INCONSISTENT:
                    logger.warning(f"⚠️ JWT inconsistency detected: {report.summary}")
                else:
                    logger.error(f"❌ JWT validation error: {report.summary}")
                    
                # Wait for next check
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("JWT Secret Drift Monitor cancelled")
                break
            except Exception as e:
                logger.error(f"JWT drift monitoring error: {e}", exc_info=True)
                # Continue monitoring even after errors
                await asyncio.sleep(self.config.check_interval_seconds)
        
        logger.info("JWT Secret Drift Monitor stopped")
    
    async def start_monitoring(self) -> None:
        """Start JWT secret drift monitoring."""
        if self.is_monitoring:
            logger.warning("JWT Secret Drift Monitor already running")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("🚀 JWT Secret Drift Monitor started")
        
        # Perform immediate validation
        try:
            report = await self._perform_validation()
            logger.info(f"Initial JWT validation: {report.overall_result.value}")
            
            if report.overall_result == ValidationResult.INCONSISTENT:
                logger.critical(f"🚨 IMMEDIATE JWT INCONSISTENCY DETECTED: {report.summary}")
                
        except Exception as e:
            logger.error(f"Initial JWT validation failed: {e}")
    
    async def stop_monitoring(self) -> None:
        """Stop JWT secret drift monitoring."""
        if not self.is_monitoring:
            return
        
        logger.info("Stopping JWT Secret Drift Monitor...")
        
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        logger.info("JWT Secret Drift Monitor stopped")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        avg_validation_time = (
            self.total_validation_time / self.validation_count 
            if self.validation_count > 0 else 0
        )
        
        status = {
            "monitoring_active": self.is_monitoring,
            "config": {
                "check_interval": self.config.check_interval_seconds,
                "alert_threshold": self.config.alert_threshold_seconds,
                "alerting_enabled": self.config.enable_alerting,
                "services_monitored": self.config.services_to_monitor
            },
            "performance": {
                "validation_count": self.validation_count,
                "average_validation_time": round(avg_validation_time, 3),
                "last_validation_time": self.last_validation_time.isoformat() if self.last_validation_time else None
            },
            "state": {
                "consecutive_failures": self.consecutive_failures,
                "drift_detected": self.drift_start_time is not None,
                "drift_start_time": self.drift_start_time.isoformat() if self.drift_start_time else None
            },
            "alerts": {
                "total_alerts": len(self.alert_history),
                "recent_alerts": len([a for a in self.alert_history 
                                   if (datetime.now(timezone.utc) - a.timestamp).total_seconds() < 3600])
            }
        }
        
        if self.last_validation:
            status["last_validation"] = {
                "timestamp": self.last_validation.validation_timestamp.isoformat(),
                "result": self.last_validation.overall_result.value,
                "summary": self.last_validation.summary,
                "services_validated": len(self.last_validation.services),
                "reachable_services": len([s for s in self.last_validation.services if s.reachable])
            }
        
        return status
    
    def get_recent_alerts(self, hours: int = 24) -> List[JWTDriftAlert]:
        """Get recent JWT drift alerts."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff]


# Global monitor instance
_jwt_drift_monitor: Optional[JWTSecretDriftMonitor] = None


def get_jwt_drift_monitor() -> JWTSecretDriftMonitor:
    """Get global JWT drift monitor instance."""
    global _jwt_drift_monitor
    if _jwt_drift_monitor is None:
        _jwt_drift_monitor = JWTSecretDriftMonitor()
    return _jwt_drift_monitor


async def start_jwt_drift_monitoring(config: Optional[MonitoringConfig] = None) -> JWTSecretDriftMonitor:
    """
    Start JWT secret drift monitoring.
    
    Args:
        config: Optional monitoring configuration
        
    Returns:
        JWTSecretDriftMonitor instance
    """
    global _jwt_drift_monitor
    
    if config:
        _jwt_drift_monitor = JWTSecretDriftMonitor(config)
    else:
        _jwt_drift_monitor = get_jwt_drift_monitor()
    
    await _jwt_drift_monitor.start_monitoring()
    return _jwt_drift_monitor


async def stop_jwt_drift_monitoring() -> None:
    """Stop JWT secret drift monitoring."""
    global _jwt_drift_monitor
    
    if _jwt_drift_monitor:
        await _jwt_drift_monitor.stop_monitoring()


def default_alert_handler(alert: JWTDriftAlert) -> None:
    """Default alert handler that logs JWT drift alerts."""
    # This would be where you'd integrate with external alerting systems
    # like Slack, PagerDuty, email, etc.
    
    if alert.level == AlertLevel.EMERGENCY:
        logger.critical(f"🚨 EMERGENCY JWT DRIFT: {alert.issue}")
    elif alert.level == AlertLevel.CRITICAL:
        logger.error(f"🔥 CRITICAL JWT DRIFT: {alert.issue}")
    elif alert.level == AlertLevel.WARNING:
        logger.warning(f"⚠️ JWT DRIFT WARNING: {alert.issue}")
    else:
        logger.info(f"ℹ️ JWT DRIFT INFO: {alert.issue}")


__all__ = [
    "AlertLevel",
    "JWTDriftAlert", 
    "MonitoringConfig",
    "JWTSecretDriftMonitor",
    "get_jwt_drift_monitor",
    "start_jwt_drift_monitoring",
    "stop_jwt_drift_monitoring",
    "default_alert_handler"
]