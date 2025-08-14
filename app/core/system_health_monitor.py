"""Enhanced system-wide health monitoring and alerting.

This module provides comprehensive health monitoring for all system components
including databases, Redis, WebSocket connections, and system resources.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from app.logging_config import central_logger
from .health_types import HealthStatus, ComponentHealth, SystemAlert, HealthCheckResult
from .health_checkers import (
    check_postgres_health, check_clickhouse_health, check_redis_health,
    check_websocket_health, check_system_resources
)
from .alert_manager import AlertManager

logger = central_logger.get_logger(__name__)


class SystemHealthMonitor:
    """Enhanced system health monitor with comprehensive checks and alerting."""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.component_health: Dict[str, ComponentHealth] = {}
        self.alert_manager = AlertManager()
        
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
        
        # Component checkers
        self.component_checkers: Dict[str, Callable] = {}
        self._register_default_checkers()
    
    def register_component_checker(self, component_name: str, checker_func: Callable) -> None:
        """Register a health checker for a component."""
        self.component_checkers[component_name] = checker_func
        logger.debug(f"Registered health checker for component: {component_name}")
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback function for alerts."""
        self.alert_manager.register_alert_callback(callback)
        logger.debug("Registered alert callback")
    
    async def start_monitoring(self) -> None:
        """Start system health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Enhanced system health monitoring started")
    
    async def stop_monitoring(self) -> None:
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
        
        logger.info("Enhanced system health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop with enhanced error handling."""
        while self._running:
            try:
                await self._perform_health_checks()
                await self._evaluate_system_health()
                await self._check_thresholds()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered components."""
        check_tasks = []
        
        for component_name, checker_func in self.component_checkers.items():
            task = asyncio.create_task(
                self._execute_health_check(component_name, checker_func)
            )
            check_tasks.append(task)
        
        if check_tasks:
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            await self._process_check_results(results)
    
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


# Agent metrics integration functions
def get_agent_metrics_collector():
    """Get agent metrics collector instance."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    return agent_metrics_collector


# Enhanced SystemHealthMonitor with agent metrics integration
class EnhancedSystemHealthMonitor(SystemHealthMonitor):
    """Extended system health monitor with agent metrics integration."""
    
    def _register_default_checkers(self):
        """Register default health checkers including agent metrics."""
        # Register agent metrics health checker
        self.register_component_checker("agent_metrics", self._check_agent_health)
        logger.debug("Registered default health checkers with agent metrics")
    
    async def _check_agent_health(self) -> Dict[str, Any]:
        """Check overall agent system health."""
        try:
            metrics_collector = get_agent_metrics_collector()
            system_overview = await metrics_collector.get_system_overview()
            
            # Calculate overall health score based on system metrics
            error_rate = system_overview.get("system_error_rate", 0.0)
            active_agents = system_overview.get("active_agents", 0)
            unhealthy_agents = system_overview.get("unhealthy_agents", 0)
            
            # Health score calculation
            if active_agents == 0:
                health_score = 1.0  # No agents running, assume healthy
            else:
                error_penalty = min(0.5, error_rate * 2)  # Cap at 50% penalty
                unhealthy_penalty = min(0.3, (unhealthy_agents / active_agents) * 0.5)
                health_score = max(0.0, 1.0 - error_penalty - unhealthy_penalty)
            
            return {
                "health_score": health_score,
                "error_count": system_overview.get("total_failures", 0),
                "metadata": {
                    "total_operations": system_overview.get("total_operations", 0),
                    "system_error_rate": error_rate,
                    "active_agents": active_agents,
                    "unhealthy_agents": unhealthy_agents,
                    "active_operations": system_overview.get("active_operations", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            return {"health_score": 0.0, "error_count": 1, "metadata": {"error": str(e)}}
    
    async def get_agent_health_details(self) -> Dict[str, Any]:
        """Get detailed agent health information."""
        try:
            metrics_collector = get_agent_metrics_collector()
            all_metrics = metrics_collector.get_all_agent_metrics()
            
            agent_health_scores = {}
            unhealthy_agents = []
            
            for agent_name, metrics in all_metrics.items():
                health_score = metrics_collector.get_health_score(agent_name)
                agent_health_scores[agent_name] = health_score
                
                if health_score < 0.7:
                    unhealthy_agents.append({
                        "name": agent_name,
                        "health_score": health_score,
                        "error_rate": metrics.error_rate,
                        "total_operations": metrics.total_operations,
                        "avg_execution_time_ms": metrics.avg_execution_time_ms
                    })
            
            return {
                "agent_count": len(all_metrics),
                "healthy_agents": len([s for s in agent_health_scores.values() if s >= 0.7]),
                "degraded_agents": len([s for s in agent_health_scores.values() if 0.5 <= s < 0.7]),
                "unhealthy_agents": len([s for s in agent_health_scores.values() if s < 0.5]),
                "agent_health_scores": agent_health_scores,
                "unhealthy_agent_details": unhealthy_agents
            }
        except Exception as e:
            logger.error(f"Error getting agent health details: {e}")
            return {"error": str(e)}

    async def _evaluate_system_health(self):
        """Evaluate overall system health and trigger system-wide alerts."""
        try:
            # Get current component health
            total_components = len(self.component_health)
            if total_components == 0:
                return
            
            healthy_count = len([h for h in self.component_health.values() 
                               if h.status == HealthStatus.HEALTHY])
            critical_count = len([h for h in self.component_health.values() 
                                if h.status == HealthStatus.CRITICAL])
            
            # Calculate system health percentage
            system_health_pct = healthy_count / total_components
            
            # Trigger system-wide alerts if needed
            if critical_count > 0 and system_health_pct < 0.5:
                await self._trigger_system_wide_alert(
                    "critical", 
                    f"System health critical: {critical_count} critical components, "
                    f"{system_health_pct:.1%} healthy"
                )
            elif system_health_pct < 0.7:
                await self._trigger_system_wide_alert(
                    "warning",
                    f"System health degraded: {system_health_pct:.1%} healthy components"
                )
                
        except Exception as e:
            logger.error(f"Error evaluating system health: {e}")
    
    async def _trigger_system_wide_alert(self, severity: str, message: str):
        """Trigger a system-wide alert."""
        alert = SystemAlert(
            alert_id=f"system_wide_{severity}_{int(time.time())}",
            component="system",
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metadata={"alert_type": "system_wide"}
        )
        
        await self._emit_alert(alert)


# Replace global instance with enhanced version
system_health_monitor = EnhancedSystemHealthMonitor()

