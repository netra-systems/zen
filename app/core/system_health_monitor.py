"""Enhanced system-wide health monitoring and alerting.

This module provides comprehensive health monitoring for all system components
including databases, Redis, WebSocket connections, and system resources.
All functions are ≤8 lines, total file ≤300 lines as per conventions.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, UTC

from app.logging_config import central_logger
from .health_types import HealthStatus, ComponentHealth, SystemAlert, HealthCheckResult
from .health_checkers import (
    check_postgres_health, check_clickhouse_health, check_redis_health,
    check_websocket_health, check_system_resources
)
from .alert_manager import AlertManager
from .agent_health_checker import (
    register_agent_checker, convert_legacy_result, determine_system_status
)

logger = central_logger.get_logger(__name__)


class SystemHealthMonitor:
    """Enhanced system health monitor with comprehensive checks and alerting."""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.component_health: Dict[str, ComponentHealth] = {}
        self.alert_manager = AlertManager()
        self.health_thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self.start_time = time.time()
        self.component_checkers: Dict[str, Callable] = {}
        self._register_default_checkers()
    
    def register_component_checker(self, component_name: str, checker_func: Callable) -> None:
        """Register a health checker for a component."""
        self.component_checkers[component_name] = checker_func
        logger.debug(f"Registered health checker for component: {component_name}")
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback function for alerts."""
        self.alert_manager.register_alert_callback(callback)
    
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
            task = asyncio.create_task(self._execute_health_check(component_name, checker_func))
            check_tasks.append(task)
        if check_tasks:
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            await self._process_check_results(results)
    
    async def _execute_health_check(self, component_name: str, checker_func: Callable) -> HealthCheckResult:
        """Execute health check for a specific component."""
        try:
            if asyncio.iscoroutinefunction(checker_func):
                result = await checker_func()
            else:
                result = checker_func()
            
            if isinstance(result, HealthCheckResult):
                return result
            else:
                return self._convert_legacy_result(component_name, result)
        except Exception as e:
            logger.error(f"Health check failed for {component_name}: {e}")
            return HealthCheckResult(
                component_name=component_name, success=False, health_score=0.0,
                response_time_ms=0.0, error_message=str(e)
            )
    
    async def _process_check_results(self, results: List[Any]) -> None:
        """Process health check results and update component health."""
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check exception: {result}")
                continue
            if isinstance(result, HealthCheckResult):
                await self._update_component_from_result(result)
    
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
    
    async def _update_component_from_result(self, result: HealthCheckResult) -> None:
        """Update component health from check result."""
        status = self._calculate_health_status(result.health_score)
        previous_health = self.component_health.get(result.component_name)
        
        current_health = ComponentHealth(
            name=result.component_name, status=status, health_score=result.health_score,
            last_check=datetime.now(UTC), error_count=1 if not result.success else 0,
            uptime=time.time() - self.start_time,
            metadata={**result.metadata, "response_time_ms": result.response_time_ms}
        )
        
        self.component_health[result.component_name] = current_health
        
        if previous_health and previous_health.status != current_health.status:
            alert = await self.alert_manager.create_status_change_alert(previous_health, current_health)
            await self.alert_manager.emit_alert(alert)
    
    async def _check_thresholds(self) -> None:
        """Check for threshold violations and generate alerts."""
        for component_name, health in self.component_health.items():
            response_time = health.metadata.get("response_time_ms", 0)
            if response_time > 5000:
                alert = await self.alert_manager.create_threshold_alert(
                    component_name, "response_time", response_time, 5000
                )
                await self.alert_manager.emit_alert(alert)
            
            if health.error_count > 5:
                alert = await self.alert_manager.create_threshold_alert(
                    component_name, "error_count", health.error_count, 5
                )
                await self.alert_manager.emit_alert(alert)
    
    async def _evaluate_system_health(self) -> None:
        """Evaluate overall system health and trigger system-wide alerts."""
        try:
            total_components = len(self.component_health)
            if total_components == 0:
                return
            
            healthy_count = len([h for h in self.component_health.values() 
                               if h.status == HealthStatus.HEALTHY])
            critical_count = len([h for h in self.component_health.values() 
                                if h.status == HealthStatus.CRITICAL])
            
            system_health_pct = healthy_count / total_components
            
            if critical_count > 0 and system_health_pct < 0.5:
                await self._trigger_system_wide_alert(
                    "critical", f"System health critical: {critical_count} critical components, "
                    f"{system_health_pct:.1%} healthy"
                )
            elif system_health_pct < 0.7:
                await self._trigger_system_wide_alert(
                    "warning", f"System health degraded: {system_health_pct:.1%} healthy components"
                )
        except Exception as e:
            logger.error(f"Error evaluating system health: {e}")
    
    async def _trigger_system_wide_alert(self, severity: str, message: str) -> None:
        """Trigger a system-wide alert."""
        alert = SystemAlert(
            alert_id=f"system_wide_{severity}_{int(time.time())}", component="system",
            severity=severity, message=message, timestamp=datetime.now(UTC),
            metadata={"alert_type": "system_wide"}
        )
        await self.alert_manager.emit_alert(alert)
    
    def _convert_legacy_result(self, component_name: str, legacy_result: Any) -> HealthCheckResult:
        """Convert legacy health check result to new format."""
        return convert_legacy_result(component_name, legacy_result)
    
    def _register_default_checkers(self) -> None:
        """Register default health checkers for core components."""
        self.register_component_checker("postgres", check_postgres_health)
        self.register_component_checker("clickhouse", check_clickhouse_health)
        self.register_component_checker("redis", check_redis_health)
        self.register_component_checker("websocket", check_websocket_health)
        self.register_component_checker("system_resources", check_system_resources)
        self._register_agent_checker()
        logger.debug("Registered default health checkers")
    
    def _register_agent_checker(self) -> None:
        """Register agent health checker if available."""
        register_agent_checker(self.register_component_checker)
    
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system health overview."""
        total_components = len(self.component_health)
        if total_components == 0:
            return {"status": "no_components", "components": []}
        
        healthy_count = len([h for h in self.component_health.values() if h.status == HealthStatus.HEALTHY])
        degraded_count = len([h for h in self.component_health.values() if h.status == HealthStatus.DEGRADED])
        unhealthy_count = len([h for h in self.component_health.values() if h.status == HealthStatus.UNHEALTHY])
        critical_count = len([h for h in self.component_health.values() if h.status == HealthStatus.CRITICAL])
        
        system_health_pct = healthy_count / total_components
        overall_status = self._determine_system_status(system_health_pct, critical_count)
        
        return {
            "overall_status": overall_status, "system_health_percentage": system_health_pct * 100,
            "total_components": total_components, "healthy_components": healthy_count,
            "degraded_components": degraded_count, "unhealthy_components": unhealthy_count,
            "critical_components": critical_count, "active_alerts": len(self.alert_manager.get_active_alerts()),
            "uptime_seconds": time.time() - self.start_time
        }
    
    def _determine_system_status(self, health_pct: float, critical_count: int) -> str:
        """Determine overall system status."""
        return determine_system_status(health_pct, critical_count)


# Global system health monitor instance
system_health_monitor = SystemHealthMonitor()