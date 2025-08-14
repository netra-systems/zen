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
            else:\n                health_score = 1.0 if health_data else 0.0\n                error_count = 0 if health_data else 1\n                metadata = {}\n            \n            # Determine status based on health score\n            status = self._calculate_health_status(health_score)\n            \n            # Update component health\n            current_time = datetime.utcnow()\n            uptime = time.time() - self.start_time\n            \n            component_health = ComponentHealth(\n                name=component_name,\n                status=status,\n                health_score=health_score,\n                last_check=current_time,\n                error_count=error_count,\n                uptime=uptime,\n                metadata={**metadata, \"check_duration\": check_duration}\n            )\n            \n            # Check for status changes and generate alerts\n            await self._update_component_health(component_health)\n            \n        except Exception as e:\n            logger.error(f\"Health check failed for {component_name}: {e}\")\n            \n            # Mark component as unhealthy\n            component_health = ComponentHealth(\n                name=component_name,\n                status=HealthStatus.CRITICAL,\n                health_score=0.0,\n                last_check=datetime.utcnow(),\n                error_count=1,\n                uptime=time.time() - self.start_time,\n                metadata={\"error\": str(e)}\n            )\n            \n            await self._update_component_health(component_health)\n    \n    def _calculate_health_status(self, health_score: float) -> HealthStatus:\n        \"\"\"Calculate health status from health score.\"\"\"\n        if health_score >= self.health_thresholds[\"healthy\"]:\n            return HealthStatus.HEALTHY\n        elif health_score >= self.health_thresholds[\"degraded\"]:\n            return HealthStatus.DEGRADED\n        elif health_score >= self.health_thresholds[\"unhealthy\"]:\n            return HealthStatus.UNHEALTHY\n        else:\n            return HealthStatus.CRITICAL\n    \n    async def _update_component_health(self, new_health: ComponentHealth):\n        \"\"\"Update component health and generate alerts if needed.\"\"\"\n        component_name = new_health.name\n        previous_health = self.component_health.get(component_name)\n        \n        # Update stored health\n        self.component_health[component_name] = new_health\n        \n        # Check for status changes\n        if previous_health and previous_health.status != new_health.status:\n            await self._generate_status_change_alert(previous_health, new_health)\n        elif not previous_health and new_health.status != HealthStatus.HEALTHY:\n            await self._generate_initial_alert(new_health)\n    \n    async def _generate_status_change_alert(self, previous: ComponentHealth, current: ComponentHealth):\n        \"\"\"Generate alert for component status change.\"\"\"\n        severity = self._get_alert_severity(current.status)\n        \n        if current.status.value in [\"unhealthy\", \"critical\"]:\n            message = f\"Component {current.name} health degraded from {previous.status.value} to {current.status.value}\"\n        elif current.status.value == \"healthy\" and previous.status.value != \"healthy\":\n            message = f\"Component {current.name} recovered to {current.status.value} from {previous.status.value}\"\n        else:\n            message = f\"Component {current.name} status changed from {previous.status.value} to {current.status.value}\"\n        \n        alert = SystemAlert(\n            alert_id=f\"status_change_{current.name}_{int(time.time())}\",\n            component=current.name,\n            severity=severity,\n            message=message,\n            timestamp=datetime.utcnow(),\n            metadata={\n                \"previous_status\": previous.status.value,\n                \"current_status\": current.status.value,\n                \"health_score\": current.health_score,\n                \"error_count\": current.error_count\n            }\n        )\n        \n        await self._emit_alert(alert)\n    \n    async def _generate_initial_alert(self, health: ComponentHealth):\n        \"\"\"Generate alert for component initial unhealthy state.\"\"\"\n        if health.status == HealthStatus.HEALTHY:\n            return\n        \n        severity = self._get_alert_severity(health.status)\n        message = f\"Component {health.name} is {health.status.value} (health score: {health.health_score:.2f})\"\n        \n        alert = SystemAlert(\n            alert_id=f\"initial_{health.name}_{int(time.time())}\",\n            component=health.name,\n            severity=severity,\n            message=message,\n            timestamp=datetime.utcnow(),\n            metadata={\n                \"status\": health.status.value,\n                \"health_score\": health.health_score,\n                \"error_count\": health.error_count\n            }\n        )\n        \n        await self._emit_alert(alert)\n    \n    def _get_alert_severity(self, status: HealthStatus) -> str:\n        \"\"\"Get alert severity based on health status.\"\"\"\n        severity_map = {\n            HealthStatus.HEALTHY: \"info\",\n            HealthStatus.DEGRADED: \"warning\",\n            HealthStatus.UNHEALTHY: \"error\",\n            HealthStatus.CRITICAL: \"critical\"\n        }\n        return severity_map.get(status, \"info\")\n    \n    async def _emit_alert(self, alert: SystemAlert):\n        \"\"\"Emit alert to all registered callbacks.\"\"\"\n        self.alerts.append(alert)\n        \n        # Keep alert history manageable\n        if len(self.alerts) > self.max_alert_history:\n            self.alerts = self.alerts[-self.max_alert_history:]\n        \n        # Log alert\n        log_level = {\n            \"info\": logger.info,\n            \"warning\": logger.warning,\n            \"error\": logger.error,\n            \"critical\": logger.critical\n        }.get(alert.severity, logger.info)\n        \n        log_level(f\"HEALTH ALERT [{alert.severity.upper()}] {alert.component}: {alert.message}\")\n        \n        # Call registered callbacks\n        for callback in self.alert_callbacks:\n            try:\n                if asyncio.iscoroutinefunction(callback):\n                    await callback(alert)\n                else:\n                    callback(alert)\n            except Exception as e:\n                logger.error(f\"Error in alert callback: {e}\")\n    \n    async def _evaluate_system_health(self):\n        \"\"\"Evaluate overall system health.\"\"\"\n        if not self.component_health:\n            return\n        \n        # Calculate overall health score\n        total_score = sum(comp.health_score for comp in self.component_health.values())\n        overall_score = total_score / len(self.component_health)\n        \n        # Count components by status\n        status_counts = {status: 0 for status in HealthStatus}\n        for comp in self.component_health.values():\n            status_counts[comp.status] += 1\n        \n        # Determine overall system status\n        if status_counts[HealthStatus.CRITICAL] > 0:\n            system_status = HealthStatus.CRITICAL\n        elif status_counts[HealthStatus.UNHEALTHY] > 0:\n            system_status = HealthStatus.UNHEALTHY\n        elif status_counts[HealthStatus.DEGRADED] > 0:\n            system_status = HealthStatus.DEGRADED\n        else:\n            system_status = HealthStatus.HEALTHY\n        \n        # Store system health metrics\n        self.system_health = {\n            \"overall_score\": overall_score,\n            \"system_status\": system_status.value,\n            \"component_count\": len(self.component_health),\n            \"status_breakdown\": {status.value: count for status, count in status_counts.items()},\n            \"last_evaluation\": datetime.utcnow().isoformat()\n        }\n    \n    def _register_default_checkers(self):\n        \"\"\"Register default health checkers.\"\"\"\n        \n        async def check_reliability_system():\n            \"\"\"Check the reliability system health.\"\"\"\n            try:\n                system_health = get_system_health()\n                if not system_health[\"agents\"]:\n                    return {\"health_score\": 1.0, \"metadata\": {\"message\": \"No agents registered yet\"}}\n                \n                healthy_agents = system_health[\"healthy_agents\"]\n                total_agents = system_health[\"total_agents\"]\n                health_score = healthy_agents / max(1, total_agents)\n                \n                return {\n                    \"health_score\": health_score,\n                    \"metadata\": {\n                        \"healthy_agents\": healthy_agents,\n                        \"total_agents\": total_agents,\n                        \"agents\": system_health[\"agents\"]\n                    }\n                }\n            except Exception:\n                return {\"health_score\": 0.5, \"metadata\": {\"error\": \"Failed to check reliability system\"}}\n        \n        # Register default checkers\n        self.register_component_checker(\"reliability_system\", check_reliability_system)\n    \n    def get_system_health(self) -> Dict[str, Any]:\n        \"\"\"Get comprehensive system health status.\"\"\"\n        return {\n            \"system_health\": getattr(self, 'system_health', {\n                \"overall_score\": 1.0,\n                \"system_status\": \"healthy\",\n                \"component_count\": 0,\n                \"status_breakdown\": {},\n                \"last_evaluation\": datetime.utcnow().isoformat()\n            }),\n            \"components\": {\n                name: {\n                    \"status\": comp.status.value,\n                    \"health_score\": comp.health_score,\n                    \"last_check\": comp.last_check.isoformat(),\n                    \"error_count\": comp.error_count,\n                    \"uptime\": comp.uptime,\n                    \"metadata\": comp.metadata\n                }\n                for name, comp in self.component_health.items()\n            },\n            \"recent_alerts\": [\n                {\n                    \"alert_id\": alert.alert_id,\n                    \"component\": alert.component,\n                    \"severity\": alert.severity,\n                    \"message\": alert.message,\n                    \"timestamp\": alert.timestamp.isoformat(),\n                    \"resolved\": alert.resolved\n                }\n                for alert in self.alerts[-20:]  # Last 20 alerts\n            ],\n            \"monitoring_info\": {\n                \"running\": self._running,\n                \"check_interval\": self.check_interval,\n                \"uptime\": time.time() - self.start_time,\n                \"registered_components\": list(self.component_checkers.keys())\n            }\n        }\n    \n    def get_component_health(self, component_name: str) -> Optional[Dict[str, Any]]:\n        \"\"\"Get health status for a specific component.\"\"\"\n        comp = self.component_health.get(component_name)\n        if not comp:\n            return None\n        \n        return {\n            \"name\": comp.name,\n            \"status\": comp.status.value,\n            \"health_score\": comp.health_score,\n            \"last_check\": comp.last_check.isoformat(),\n            \"error_count\": comp.error_count,\n            \"uptime\": comp.uptime,\n            \"metadata\": comp.metadata\n        }\n    \n    def resolve_alert(self, alert_id: str) -> bool:\n        \"\"\"Mark an alert as resolved.\"\"\"\n        for alert in self.alerts:\n            if alert.alert_id == alert_id:\n                alert.resolved = True\n                logger.info(f\"Alert {alert_id} marked as resolved\")\n                return True\n        return False\n\n\n# Global system health monitor instance\nsystem_health_monitor = SystemHealthMonitor()