"""Enhanced system-wide health monitoring and alerting.

This module provides comprehensive health monitoring for all system components
including databases, Redis, WebSocket connections, and system resources.
All functions are  <= 8 lines, total file  <= 300 lines as per conventions.
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.agent_health_checker import (
    convert_legacy_result,
    determine_system_status,
    register_agent_checker,
)
from netra_backend.app.core.health_checkers import (
    check_clickhouse_health,
    check_postgres_health,
    check_redis_health,
    check_system_resources,
    check_websocket_health,
)
from netra_backend.app.core.health_types import (
    ComponentHealth,
    HealthCheckResult,
    HealthStatus,
    SystemAlert,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.observability.alert_manager import HealthAlertManager

logger = central_logger.get_logger(__name__)


class SystemHealthMonitor:
    """Enhanced system health monitor with comprehensive checks and alerting."""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self._initialize_core_components()
        self._initialize_monitoring_state()
        self._register_default_checkers()
    
    def _initialize_core_components(self) -> None:
        """Initialize core health monitoring components."""
        self.component_health: Dict[str, ComponentHealth] = {}
        self.alert_manager = HealthAlertManager()
        self.health_thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        self.component_checkers: Dict[str, Callable] = {}
    
    def _initialize_monitoring_state(self) -> None:
        """Initialize monitoring state variables."""
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self.start_time = time.time()
    
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
        await self._cleanup_monitoring_task()
        logger.info("Enhanced system health monitoring stopped")
    
    async def _cleanup_monitoring_task(self) -> None:
        """Clean up the monitoring task if it exists."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            await self._wait_for_task_cancellation()
    
    async def _wait_for_task_cancellation(self) -> None:
        """Wait for monitoring task to be cancelled."""
        try:
            await self._monitoring_task
        except asyncio.CancelledError:
            pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop with enhanced error handling."""
        while self._running:
            try:
                await self._execute_monitoring_cycle()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e)
    
    async def _execute_monitoring_cycle(self) -> None:
        """Execute one complete monitoring cycle."""
        await self._perform_health_checks()
        await self._evaluate_system_health()
        await self._check_thresholds()
    
    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle error in monitoring loop."""
        logger.error(f"Error in health monitoring loop: {error}")
        await asyncio.sleep(5)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered components."""
        check_tasks = self._create_health_check_tasks()
        if check_tasks:
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            await self._process_check_results(results)
    
    def _create_health_check_tasks(self) -> list:
        """Create health check tasks for all components."""
        check_tasks = []
        for component_name, checker_func in self.component_checkers.items():
            task = asyncio.create_task(self._execute_health_check(component_name, checker_func))
            check_tasks.append(task)
        return check_tasks
    
    async def _execute_health_check(self, component_name: str, checker_func: Callable) -> HealthCheckResult:
        """Execute health check for a specific component."""
        try:
            result = await self._call_checker_function(checker_func)
            return self._process_check_result(component_name, result)
        except Exception as e:
            return self._handle_health_check_error(component_name, e)
    
    def _handle_health_check_error(self, component_name: str, error: Exception) -> HealthCheckResult:
        """Handle health check error and create result."""
        logger.error(f"Health check failed for {component_name}: {error}")
        return self._create_failed_health_result(component_name, error)
    
    async def _call_checker_function(self, checker_func: Callable):
        """Call checker function handling both sync and async."""
        if asyncio.iscoroutinefunction(checker_func):
            return await checker_func()
        else:
            return checker_func()
    
    def _process_check_result(self, component_name: str, result) -> HealthCheckResult:
        """Process health check result and convert if needed."""
        if isinstance(result, HealthCheckResult):
            return result
        else:
            return self._convert_legacy_result(component_name, result)
    
    def _create_failed_health_result(self, component_name: str, error: Exception) -> HealthCheckResult:
        """Create health result for failed check."""
        return HealthCheckResult(
            component_name=component_name, success=False, health_score=0.0,
            response_time_ms=0.0, error_message=str(error)
        )
    
    async def _process_check_results(self, results: List[Any]) -> None:
        """Process health check results and update component health."""
        for result in results:
            await self._process_individual_result(result)
    
    async def _process_individual_result(self, result: Any) -> None:
        """Process individual health check result."""
        if isinstance(result, Exception):
            logger.error(f"Health check exception: {result}")
        elif isinstance(result, HealthCheckResult):
            await self._update_component_from_result(result)
    
    def _calculate_health_status(self, health_score: float) -> HealthStatus:
        """Calculate health status from health score."""
        if health_score >= self.health_thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif health_score >= self.health_thresholds["degraded"]:
            return HealthStatus.DEGRADED
        return self._determine_unhealthy_or_critical_status(health_score)
    
    def _determine_unhealthy_or_critical_status(self, health_score: float) -> HealthStatus:
        """Determine if health status is unhealthy or critical."""
        if health_score >= self.health_thresholds["unhealthy"]:
            return HealthStatus.UNHEALTHY
        return HealthStatus.CRITICAL
    
    async def _update_component_from_result(self, result: HealthCheckResult) -> None:
        """Update component health from check result."""
        status = self._calculate_health_status(result.health_score)
        previous_health = self.component_health.get(result.component_name)
        current_health = self._create_component_health(result, status)
        self.component_health[result.component_name] = current_health
        await self._check_for_status_change_alert(previous_health, current_health)
    
    def _create_component_health(self, result: HealthCheckResult, status: HealthStatus) -> ComponentHealth:
        """Create ComponentHealth object from result."""
        return ComponentHealth(
            name=result.component_name, status=status, health_score=result.health_score,
            last_check=datetime.now(UTC), error_count=self._calculate_error_count(result),
            uptime=self._calculate_uptime(), metadata=self._create_metadata(result)
        )
    
    def _calculate_error_count(self, result: HealthCheckResult) -> int:
        """Calculate error count from result."""
        return 1 if not result.success else 0
    
    def _calculate_uptime(self) -> float:
        """Calculate system uptime in seconds."""
        return time.time() - self.start_time
    
    def _create_metadata(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Create metadata dictionary from result."""
        return {**result.metadata, "response_time_ms": result.response_time_ms}
    
    async def _check_for_status_change_alert(self, previous_health: Optional[ComponentHealth], 
                                           current_health: ComponentHealth) -> None:
        """Check if status changed and emit alert if needed."""
        if previous_health and previous_health.status != current_health.status:
            alert = await self.alert_manager.create_status_change_alert(previous_health, current_health)
            await self.alert_manager.emit_alert(alert)
    
    async def _check_thresholds(self) -> None:
        """Check for threshold violations and generate alerts."""
        for component_name, health in self.component_health.items():
            await self._check_response_time_threshold(component_name, health)
            await self._check_error_count_threshold(component_name, health)
    
    async def _check_response_time_threshold(self, component_name: str, health: ComponentHealth) -> None:
        """Check response time threshold for component."""
        response_time = health.metadata.get("response_time_ms", 0)
        if response_time > 5000:
            alert = await self.alert_manager.create_threshold_alert(
                component_name, "response_time", response_time, 5000
            )
            await self.alert_manager.emit_alert(alert)
    
    async def _check_error_count_threshold(self, component_name: str, health: ComponentHealth) -> None:
        """Check error count threshold for component."""
        if health.error_count > 5:
            alert = await self.alert_manager.create_threshold_alert(
                component_name, "error_count", health.error_count, 5
            )
            await self.alert_manager.emit_alert(alert)
    
    async def _evaluate_system_health(self) -> None:
        """Evaluate overall system health and trigger system-wide alerts."""
        try:
            if not self.component_health:
                return
            await self._process_system_health_evaluation()
        except Exception as e:
            logger.error(f"Error evaluating system health: {e}")
    
    async def _process_system_health_evaluation(self) -> None:
        """Process system health evaluation and alerts."""
        health_stats = self._calculate_health_statistics()
        await self._evaluate_and_alert_system_health(health_stats)
    
    def _calculate_health_statistics(self) -> Dict[str, Any]:
        """Calculate system health statistics."""
        total_components = len(self.component_health)
        healthy_count = self._count_components_with_status(HealthStatus.HEALTHY)
        critical_count = self._count_components_with_status(HealthStatus.CRITICAL)
        return self._create_health_stats_dict(total_components, healthy_count, critical_count)
    
    def _create_health_stats_dict(self, total: int, healthy: int, critical: int) -> Dict[str, Any]:
        """Create health statistics dictionary."""
        return {
            "total": total, "healthy": healthy, "critical": critical,
            "health_pct": healthy / total if total > 0 else 0
        }
    
    async def _evaluate_and_alert_system_health(self, stats: Dict[str, Any]) -> None:
        """Evaluate health stats and trigger alerts."""
        if self._is_critical_system_health(stats):
            await self._alert_critical_system_health(stats)
        elif self._is_degraded_system_health(stats):
            await self._alert_degraded_system_health(stats)
    
    def _is_critical_system_health(self, stats: Dict[str, Any]) -> bool:
        """Check if system health is critical."""
        return stats["critical"] > 0 and stats["health_pct"] <= 0.5
    
    def _is_degraded_system_health(self, stats: Dict[str, Any]) -> bool:
        """Check if system health is degraded."""
        return stats["health_pct"] < 0.7
    
    async def _alert_critical_system_health(self, stats: Dict[str, Any]) -> None:
        """Trigger critical system health alert."""
        message = f"System health critical: {stats['critical']} critical components, {stats['health_pct']:.1%} healthy"
        await self._trigger_system_wide_alert("critical", message)
    
    async def _alert_degraded_system_health(self, stats: Dict[str, Any]) -> None:
        """Trigger degraded system health alert."""
        message = f"System health degraded: {stats['health_pct']:.1%} healthy components"
        await self._trigger_system_wide_alert("warning", message)
    
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
        self._register_core_component_checkers()
        self._register_agent_checker()
        logger.debug("Registered default health checkers")
    
    def _register_core_component_checkers(self) -> None:
        """Register health checkers for core system components."""
        self.register_component_checker("postgres", check_postgres_health)
        self.register_component_checker("clickhouse", check_clickhouse_health)
        self.register_component_checker("redis", check_redis_health)
        self.register_component_checker("websocket", check_websocket_health)
        self.register_component_checker("system_resources", check_system_resources)
    
    def _register_agent_checker(self) -> None:
        """Register agent health checker if available."""
        register_agent_checker(self.register_component_checker)
    
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system health overview."""
        total_components = len(self.component_health)
        if total_components == 0:
            return {"status": "no_components", "components": []}
        
        component_counts = self._count_components_by_status()
        return self._build_system_overview_response(total_components, component_counts)
    
    def _count_components_by_status(self) -> Dict[str, int]:
        """Count components by their health status."""
        return {
            "healthy": self._count_components_with_status(HealthStatus.HEALTHY),
            "degraded": self._count_components_with_status(HealthStatus.DEGRADED),
            "unhealthy": self._count_components_with_status(HealthStatus.UNHEALTHY),
            "critical": self._count_components_with_status(HealthStatus.CRITICAL)
        }
    
    def _count_components_with_status(self, status: HealthStatus) -> int:
        """Count components with specific health status."""
        return len([h for h in self.component_health.values() if h.status == status])
    
    def _build_system_overview_response(self, total_components: int, counts: Dict[str, int]) -> Dict[str, Any]:
        """Build comprehensive system overview response."""
        health_pct = counts["healthy"] / total_components
        overall_status = self._determine_system_status(health_pct, counts["critical"])
        return self._create_overview_dict(overall_status, health_pct, total_components, counts)
    
    def _create_overview_dict(self, overall_status: str, health_pct: float, 
                             total_components: int, counts: Dict[str, int]) -> Dict[str, Any]:
        """Create system overview dictionary."""
        base_overview = self._build_base_overview_data(overall_status, health_pct, total_components)
        component_data = self._build_component_overview_data(counts)
        return {**base_overview, **component_data}
    
    def _build_base_overview_data(self, overall_status: str, health_pct: float, total_components: int) -> Dict[str, Any]:
        """Build base overview data dictionary."""
        return {
            "overall_status": overall_status, "system_health_percentage": health_pct * 100,
            "total_components": total_components, "uptime_seconds": self._calculate_uptime()
        }
    
    def _build_component_overview_data(self, counts: Dict[str, int]) -> Dict[str, Any]:
        """Build component overview data dictionary."""
        return {
            "healthy_components": counts["healthy"], "degraded_components": counts["degraded"],
            "unhealthy_components": counts["unhealthy"], "critical_components": counts["critical"],
            "active_alerts": len(self.alert_manager.get_active_alerts())
        }
    
    def _determine_system_status(self, health_pct: float, critical_count: int) -> str:
        """Determine overall system status."""
        return determine_system_status(health_pct, critical_count)


# Global system health monitor instance
system_health_monitor = SystemHealthMonitor()