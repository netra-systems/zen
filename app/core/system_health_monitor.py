"""System-wide health monitoring and alerting.

This module provides comprehensive health monitoring for all system components
including agents, WebSocket connections, databases, and external services.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from app.logging_config import central_logger
from .reliability import get_system_health

logger = central_logger.get_logger(__name__)


class HealthStatus(Enum):
    """Overall health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    name: str
    status: HealthStatus
    health_score: float  # 0.0 to 1.0
    last_check: datetime
    error_count: int = 0
    uptime: float = 0.0  # in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """System health alert."""
    alert_id: str
    component: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class SystemHealthMonitor:
    """Monitors overall system health and generates alerts."""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.component_health: Dict[str, ComponentHealth] = {}
        self.alerts: List[SystemAlert] = []
        self.max_alert_history = 1000
        
        # Health thresholds
        self.health_thresholds = {
            "healthy": 0.8,
            "degraded": 0.5,
            "unhealthy": 0.2
        }
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self.start_time = time.time()
        
        # Alert callbacks
        self.alert_callbacks: List[callable] = []
        
        # Component checkers
        self.component_checkers: Dict[str, callable] = {}
        self._register_default_checkers()
    
    def register_component_checker(self, component_name: str, checker_func: callable):
        """Register a health checker for a component."""
        self.component_checkers[component_name] = checker_func
        logger.debug(f"Registered health checker for component: {component_name}")
    
    def register_alert_callback(self, callback: callable):
        """Register a callback function for alerts."""
        self.alert_callbacks.append(callback)
        logger.debug("Registered alert callback")
    
    async def start_monitoring(self):
        """Start system health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("System health monitoring started")
    
    async def stop_monitoring(self):
        """Stop system health monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._perform_health_checks()
                await self._evaluate_system_health()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief delay before retry
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered components."""
        check_tasks = []
        
        for component_name, checker_func in self.component_checkers.items():
            task = asyncio.create_task(
                self._check_component_health(component_name, checker_func)
            )
            check_tasks.append(task)
        
        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _check_component_health(self, component_name: str, checker_func: callable):
        """Check health of a specific component."""
        try:
            start_time = time.time()
            health_data = await checker_func()
            check_duration = time.time() - start_time
            
            # Parse health data
            if isinstance(health_data, dict):
                health_score = health_data.get("health_score", 1.0)
                error_count = health_data.get("error_count", 0)
                metadata = health_data.get("metadata", {})
            elif isinstance(health_data, (int, float)):
                health_score = float(health_data)
                error_count = 0
                metadata = {}
            else:
                health_score = 1.0 if health_data else 0.0
                error_count = 0 if health_data else 1
                metadata = {}
            
            # Determine status based on health score
            status = self._calculate_health_status(health_score)
            
            # Update component health
            current_time = datetime.utcnow()
            uptime = time.time() - self.start_time
            
            component_health = ComponentHealth(
                name=component_name,
                status=status,
                health_score=health_score,
                last_check=current_time,
                error_count=error_count,
                uptime=uptime,
                metadata={**metadata, "check_duration": check_duration}
            )
            
            # Check for status changes and generate alerts
            await self._update_component_health(component_health)
            
        except Exception as e:
            logger.error(f"Health check failed for {component_name}: {e}")
            
            # Mark component as unhealthy
            component_health = ComponentHealth(
                name=component_name,
                status=HealthStatus.CRITICAL,
                health_score=0.0,
                last_check=datetime.utcnow(),
                error_count=1,
                uptime=time.time() - self.start_time,
                metadata={"error": str(e)}
            )
            
            await self._update_component_health(component_health)
    
    def _calculate_health_status(self, health_score: float) -> HealthStatus:
        """Calculate health status from health score."""
        if health_score >= self.health_thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif health_score >= self.health_thresholds["degraded"]:
            return HealthStatus.DEGRADED
        elif health_score >= self.health_thresholds["unhealthy"]:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL
    
    async def _update_component_health(self, new_health: ComponentHealth):
        """Update component health and generate alerts if needed."""
        component_name = new_health.name
        previous_health = self.component_health.get(component_name)
        
        # Update stored health
        self.component_health[component_name] = new_health
        
        # Check for status changes
        if previous_health and previous_health.status != new_health.status:
            await self._generate_status_change_alert(previous_health, new_health)
        elif not previous_health and new_health.status != HealthStatus.HEALTHY:
            await self._generate_initial_alert(new_health)
    
    async def _generate_status_change_alert(self, previous: ComponentHealth, current: ComponentHealth):
        """Generate alert for component status change."""
        severity = self._get_alert_severity(current.status)
        
        if current.status.value in ["unhealthy", "critical"]:
            message = f"Component {current.name} health degraded from {previous.status.value} to {current.status.value}"
        elif current.status.value == "healthy" and previous.status.value != "healthy":
            message = f"Component {current.name} recovered to {current.status.value} from {previous.status.value}"
        else:
            message = f"Component {current.name} status changed from {previous.status.value} to {current.status.value}"
        
        alert = SystemAlert(
            alert_id=f"status_change_{current.name}_{int(time.time())}",
            component=current.name,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metadata={
                "previous_status": previous.status.value,
                "current_status": current.status.value,
                "health_score": current.health_score,
                "error_count": current.error_count
            }
        )
        
        await self._emit_alert(alert)
    
    async def _generate_initial_alert(self, health: ComponentHealth):
        """Generate alert for component initial unhealthy state."""
        if health.status == HealthStatus.HEALTHY:
            return
        
        severity = self._get_alert_severity(health.status)
        message = f"Component {health.name} is {health.status.value} (health score: {health.health_score:.2f})"
        
        alert = SystemAlert(
            alert_id=f"initial_{health.name}_{int(time.time())}",
            component=health.name,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metadata={
                "status": health.status.value,
                "health_score": health.health_score,
                "error_count": health.error_count
            }
        )
        
        await self._emit_alert(alert)
    
    def _get_alert_severity(self, status: HealthStatus) -> str:
        """Get alert severity based on health status."""
        severity_map = {
            HealthStatus.HEALTHY: "info",
            HealthStatus.DEGRADED: "warning",
            HealthStatus.UNHEALTHY: "error",
            HealthStatus.CRITICAL: "critical"
        }
        return severity_map.get(status, "info")
    
    async def _emit_alert(self, alert: SystemAlert):
        """Emit alert to all registered callbacks."""
        self.alerts.append(alert)
        
        # Keep alert history manageable
        if len(self.alerts) > self.max_alert_history:
            self.alerts = self.alerts[-self.max_alert_history:]
        
        # Log alert
        log_level = {
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical
        }.get(alert.severity, logger.info)
        
        log_level(f"HEALTH ALERT [{alert.severity.upper()}] {alert.component}: {alert.message}")
        
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")


# Global system health monitor instance
system_health_monitor = SystemHealthMonitor()