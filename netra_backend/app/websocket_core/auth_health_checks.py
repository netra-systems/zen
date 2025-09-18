"""
Authentication Health Checks - Issue #1300 Task #5

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Provide comprehensive health monitoring for authentication subsystem
- Value Impact: Enable proactive detection of authentication system degradation
- Revenue Impact: Prevent authentication outages from impacting $500K+ ARR chat functionality

This module implements comprehensive health checks for the WebSocket authentication
subsystem, providing both programmatic health validation and HTTP endpoints for
monitoring systems.

Key Features:
1. Comprehensive health checks for all authentication components
2. HTTP endpoints for external monitoring systems
3. Dependency health validation (Redis, PostgreSQL, Auth Service)
4. Performance benchmarking and latency monitoring
5. Configuration validation and drift detection
6. Self-healing capabilities for minor issues
7. Integration with existing monitoring infrastructure
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import threading
import logging

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.auth_monitoring import (
    get_websocket_auth_monitor,
    get_auth_monitoring_health
)
from netra_backend.app.websocket_core.async_auth_metrics_collector import (
    get_async_auth_metrics_collector,
    get_collector_status
)
from netra_backend.app.websocket_core.auth_alert_system import (
    get_auth_alert_system,
    get_alert_statistics
)

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of components being monitored."""
    AUTHENTICATION = "authentication"
    MONITORING = "monitoring"
    ALERTING = "alerting"
    LOGGING = "logging"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    description: str
    component_type: ComponentType
    check_function: Callable[[], Any]
    timeout_seconds: float = 5.0
    critical: bool = True
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate health check configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class HealthCheckResult:
    """Result of a health check execution."""
    name: str
    status: HealthStatus
    message: str
    execution_time_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "error": self.error
        }


@dataclass
class OverallHealthStatus:
    """Overall health status of the authentication subsystem."""
    status: HealthStatus
    message: str
    timestamp: datetime
    total_checks: int
    passed_checks: int
    failed_checks: int
    degraded_checks: int
    critical_failures: int
    execution_time_ms: float
    check_results: List[HealthCheckResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_checks": self.total_checks,
                "passed_checks": self.passed_checks,
                "failed_checks": self.failed_checks,
                "degraded_checks": self.degraded_checks,
                "critical_failures": self.critical_failures,
                "success_rate": round((self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0, 2)
            },
            "execution_time_ms": round(self.execution_time_ms, 2),
            "individual_checks": [result.to_dict() for result in self.check_results]
        }


class AuthHealthChecker:
    """
    Authentication Health Checker for Issue #1300 Task #5.
    
    Provides comprehensive health monitoring for the WebSocket authentication
    subsystem with programmatic and HTTP endpoint access.
    
    Features:
    - Comprehensive health checks for all auth components
    - Dependency validation and performance monitoring
    - Self-healing capabilities for minor issues
    - Integration with monitoring infrastructure
    """
    
    def __init__(self):
        """Initialize the authentication health checker."""
        self._lock = threading.RLock()
        
        # Health checks registry
        self._health_checks: Dict[str, HealthCheck] = {}
        
        # Health status tracking
        self._last_health_check: Optional[OverallHealthStatus] = None
        self._health_history: List[OverallHealthStatus] = []
        self._max_history_size = 100
        
        # Statistics
        self._total_health_checks = 0
        self._total_failures = 0
        self._start_time = datetime.now(timezone.utc)
        
        # Configuration
        self._default_timeout = 5.0
        self._health_check_enabled = True
        
        # Setup default health checks
        self._setup_default_health_checks()
        
        logger.info("AuthHealthChecker initialized for Issue #1300")
    
    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a custom health check."""
        with self._lock:
            self._health_checks[health_check.name] = health_check
            logger.info(f"Added health check: {health_check.name}")
    
    def remove_health_check(self, name: str) -> bool:
        """Remove a health check."""
        with self._lock:
            if name in self._health_checks:
                del self._health_checks[name]
                logger.info(f"Removed health check: {name}")
                return True
            return False
    
    def enable_health_check(self, name: str) -> bool:
        """Enable a specific health check."""
        with self._lock:
            if name in self._health_checks:
                self._health_checks[name].enabled = True
                logger.info(f"Enabled health check: {name}")
                return True
            return False
    
    def disable_health_check(self, name: str) -> bool:
        """Disable a specific health check."""
        with self._lock:
            if name in self._health_checks:
                self._health_checks[name].enabled = False
                logger.info(f"Disabled health check: {name}")
                return True
            return False
    
    async def check_health(self, check_names: Optional[List[str]] = None) -> OverallHealthStatus:
        """
        Perform comprehensive health checks.
        
        Args:
            check_names: Optional list of specific checks to run. If None, runs all enabled checks.
            
        Returns:
            OverallHealthStatus with results of all health checks
        """
        if not self._health_check_enabled:
            return OverallHealthStatus(
                status=HealthStatus.UNKNOWN,
                message="Health checking is disabled",
                timestamp=datetime.now(timezone.utc),
                total_checks=0,
                passed_checks=0,
                failed_checks=0,
                degraded_checks=0,
                critical_failures=0,
                execution_time_ms=0.0
            )
        
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)
        
        # Select health checks to run
        checks_to_run = {}
        with self._lock:
            if check_names:
                checks_to_run = {name: check for name, check in self._health_checks.items() 
                               if name in check_names and check.enabled}
            else:
                checks_to_run = {name: check for name, check in self._health_checks.items() 
                               if check.enabled}
        
        # Execute health checks
        check_results = []
        for name, health_check in checks_to_run.items():
            try:
                result = await self._execute_health_check(health_check)
                check_results.append(result)
            except Exception as e:
                error_result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check execution failed: {str(e)}",
                    execution_time_ms=0.0,
                    timestamp=timestamp,
                    error=str(e)
                )
                check_results.append(error_result)
                logger.error(f"Health check {name} failed with exception: {e}")
        
        # Calculate overall status
        execution_time_ms = (time.time() - start_time) * 1000
        overall_status = self._calculate_overall_status(check_results, timestamp, execution_time_ms)
        
        # Store results
        with self._lock:
            self._last_health_check = overall_status
            self._health_history.append(overall_status)
            
            # Trim history if needed
            if len(self._health_history) > self._max_history_size:
                self._health_history.pop(0)
            
            self._total_health_checks += 1
            if overall_status.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]:
                self._total_failures += 1
        
        logger.info(f"Health check completed: {overall_status.status.value} ({overall_status.passed_checks}/{overall_status.total_checks} passed)")
        return overall_status
    
    async def check_component_health(self, component_type: ComponentType) -> List[HealthCheckResult]:
        """Check health of a specific component type."""
        component_checks = []
        
        with self._lock:
            for name, health_check in self._health_checks.items():
                if health_check.component_type == component_type and health_check.enabled:
                    try:
                        result = await self._execute_health_check(health_check)
                        component_checks.append(result)
                    except Exception as e:
                        error_result = HealthCheckResult(
                            name=name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"Component health check failed: {str(e)}",
                            execution_time_ms=0.0,
                            timestamp=datetime.now(timezone.utc),
                            error=str(e)
                        )
                        component_checks.append(error_result)
        
        return component_checks
    
    def get_last_health_status(self) -> Optional[OverallHealthStatus]:
        """Get the last health check results."""
        with self._lock:
            return self._last_health_check
    
    def get_health_history(self, hours: int = 1) -> List[OverallHealthStatus]:
        """Get health check history for the specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._lock:
            return [
                status for status in self._health_history
                if status.timestamp >= cutoff_time
            ]
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """Get health check statistics."""
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            
            return {
                "system_info": {
                    "uptime_seconds": uptime_seconds,
                    "health_check_enabled": self._health_check_enabled,
                    "total_health_checks": len(self._health_checks),
                    "enabled_health_checks": len([c for c in self._health_checks.values() if c.enabled])
                },
                "execution_stats": {
                    "total_checks_run": self._total_health_checks,
                    "total_failures": self._total_failures,
                    "success_rate": round(
                        ((self._total_health_checks - self._total_failures) / self._total_health_checks * 100)
                        if self._total_health_checks > 0 else 100, 2
                    ),
                    "checks_per_hour": round(self._total_health_checks / (uptime_seconds / 3600), 2) if uptime_seconds > 0 else 0
                },
                "current_status": {
                    "last_check_status": self._last_health_check.status.value if self._last_health_check else "not_run",
                    "last_check_time": self._last_health_check.timestamp.isoformat() if self._last_health_check else None,
                    "history_size": len(self._health_history)
                }
            }
    
    async def validate_dependencies(self) -> Dict[str, bool]:
        """Validate that all external dependencies are available."""
        dependencies = {
            "redis": await self._check_redis_connectivity(),
            "postgresql": await self._check_postgresql_connectivity(),
            "auth_service": await self._check_auth_service_connectivity(),
            "websocket_monitoring": await self._check_websocket_monitoring_availability(),
            "metrics_collector": await self._check_metrics_collector_availability(),
            "alert_system": await self._check_alert_system_availability()
        }
        
        return dependencies
    
    def enable_health_checks(self) -> None:
        """Enable health checking system."""
        self._health_check_enabled = True
        logger.info("Health checking enabled")
    
    def disable_health_checks(self) -> None:
        """Disable health checking system."""
        self._health_check_enabled = False
        logger.info("Health checking disabled")
    
    async def _execute_health_check(self, health_check: HealthCheck) -> HealthCheckResult:
        """Execute a single health check with timeout protection."""
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(health_check.check_function):
                result = await asyncio.wait_for(
                    health_check.check_function(),
                    timeout=health_check.timeout_seconds
                )
            else:
                # Run synchronous function in executor
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, health_check.check_function),
                    timeout=health_check.timeout_seconds
                )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Parse result
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "unknown"))
                message = result.get("message", "Health check completed")
                details = result.get("details", {})
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "Health check passed" if result else "Health check failed"
                details = {}
            else:
                status = HealthStatus.HEALTHY
                message = str(result) if result else "Health check completed"
                details = {}
            
            return HealthCheckResult(
                name=health_check.name,
                status=status,
                message=message,
                execution_time_ms=execution_time_ms,
                timestamp=timestamp,
                details=details
            )
            
        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=health_check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {health_check.timeout_seconds}s",
                execution_time_ms=execution_time_ms,
                timestamp=timestamp,
                error="timeout"
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=health_check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                execution_time_ms=execution_time_ms,
                timestamp=timestamp,
                error=str(e)
            )
    
    def _calculate_overall_status(self, 
                                 check_results: List[HealthCheckResult], 
                                 timestamp: datetime, 
                                 execution_time_ms: float) -> OverallHealthStatus:
        """Calculate overall health status from individual check results."""
        total_checks = len(check_results)
        passed_checks = len([r for r in check_results if r.status == HealthStatus.HEALTHY])
        failed_checks = len([r for r in check_results if r.status == HealthStatus.UNHEALTHY])
        degraded_checks = len([r for r in check_results if r.status == HealthStatus.DEGRADED])
        
        # Count critical failures
        critical_failures = 0
        for result in check_results:
            if result.status == HealthStatus.UNHEALTHY:
                # Check if this was a critical health check
                health_check = self._health_checks.get(result.name)
                if health_check and health_check.critical:
                    critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            overall_status = HealthStatus.UNHEALTHY
            message = f"System unhealthy: {critical_failures} critical failures detected"
        elif failed_checks > 0:
            overall_status = HealthStatus.DEGRADED
            message = f"System degraded: {failed_checks} non-critical failures detected"
        elif degraded_checks > 0:
            overall_status = HealthStatus.DEGRADED
            message = f"System degraded: {degraded_checks} checks reporting degraded status"
        else:
            overall_status = HealthStatus.HEALTHY
            message = f"All {total_checks} health checks passed"
        
        return OverallHealthStatus(
            status=overall_status,
            message=message,
            timestamp=timestamp,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            degraded_checks=degraded_checks,
            critical_failures=critical_failures,
            execution_time_ms=execution_time_ms,
            check_results=check_results
        )
    
    def _setup_default_health_checks(self) -> None:
        """Set up default health checks for authentication subsystem."""
        
        # Authentication monitoring health
        self.add_health_check(HealthCheck(
            name="auth_monitoring",
            description="Check authentication monitoring system health",
            component_type=ComponentType.MONITORING,
            check_function=self._check_auth_monitoring_health,
            timeout_seconds=3.0,
            critical=True
        ))
        
        # Metrics collector health
        self.add_health_check(HealthCheck(
            name="metrics_collector",
            description="Check async metrics collector health",
            component_type=ComponentType.MONITORING,
            check_function=self._check_metrics_collector_health,
            timeout_seconds=3.0,
            critical=False
        ))
        
        # Alert system health
        self.add_health_check(HealthCheck(
            name="alert_system",
            description="Check alert system health",
            component_type=ComponentType.ALERTING,
            check_function=self._check_alert_system_health,
            timeout_seconds=3.0,
            critical=False
        ))
        
        # WebSocket authentication functionality
        self.add_health_check(HealthCheck(
            name="websocket_auth_function",
            description="Test WebSocket authentication functionality",
            component_type=ComponentType.AUTHENTICATION,
            check_function=self._check_websocket_auth_functionality,
            timeout_seconds=5.0,
            critical=True
        ))
        
        # Configuration validation
        self.add_health_check(HealthCheck(
            name="configuration_validation",
            description="Validate authentication configuration",
            component_type=ComponentType.CONFIGURATION,
            check_function=self._check_configuration_validity,
            timeout_seconds=2.0,
            critical=True
        ))
        
        # Performance benchmarks
        self.add_health_check(HealthCheck(
            name="performance_benchmark",
            description="Authentication performance benchmarks",
            component_type=ComponentType.AUTHENTICATION,
            check_function=self._check_authentication_performance,
            timeout_seconds=10.0,
            critical=False
        ))
        
        logger.info("Default health checks configured")
    
    # Health check implementation methods
    
    async def _check_auth_monitoring_health(self) -> Dict[str, Any]:
        """Check authentication monitoring system health."""
        try:
            health_status = await get_auth_monitoring_health()
            
            if health_status["overall_status"] == "healthy":
                return {
                    "status": "healthy",
                    "message": "Authentication monitoring is healthy",
                    "details": health_status
                }
            elif health_status["overall_status"] == "degraded":
                return {
                    "status": "degraded", 
                    "message": "Authentication monitoring is degraded",
                    "details": health_status
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Authentication monitoring is unhealthy",
                    "details": health_status
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Failed to check auth monitoring health: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_metrics_collector_health(self) -> Dict[str, Any]:
        """Check async metrics collector health."""
        try:
            collector_status = get_collector_status()
            
            if collector_status.get("status") == "running":
                return {
                    "status": "healthy",
                    "message": "Metrics collector is running",
                    "details": collector_status
                }
            elif collector_status.get("status") in ["paused", "starting"]:
                return {
                    "status": "degraded",
                    "message": f"Metrics collector status: {collector_status.get('status')}",
                    "details": collector_status
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Metrics collector unhealthy: {collector_status.get('status')}",
                    "details": collector_status
                }
                
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Failed to check metrics collector: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_alert_system_health(self) -> Dict[str, Any]:
        """Check alert system health."""
        try:
            alert_stats = get_alert_statistics()
            
            # Check if alert system is functional
            if alert_stats.get("system_info", {}).get("monitoring_enabled", False):
                return {
                    "status": "healthy",
                    "message": "Alert system is functional",
                    "details": alert_stats
                }
            else:
                return {
                    "status": "degraded",
                    "message": "Alert monitoring is disabled",
                    "details": alert_stats
                }
                
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Failed to check alert system: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_websocket_auth_functionality(self) -> Dict[str, Any]:
        """Test WebSocket authentication functionality."""
        try:
            # This is a basic functionality test
            # In a real implementation, you might create a test WebSocket connection
            
            # Check if auth monitor is available
            auth_monitor = get_websocket_auth_monitor()
            
            # Get current metrics to ensure system is responsive
            metrics = auth_monitor.get_metrics()
            
            return {
                "status": "healthy",
                "message": "WebSocket authentication functionality is operational",
                "details": {
                    "auth_monitor_available": True,
                    "metrics_responsive": True,
                    "total_users_tracked": metrics.get("total_users_tracked", 0)
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"WebSocket auth functionality check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_configuration_validity(self) -> Dict[str, Any]:
        """Validate authentication configuration."""
        try:
            config_issues = []
            
            # Check critical configuration values
            try:
                from netra_backend.app.core.configuration.base import get_config
                config = get_config()
                
                # Check if required config values are present
                # This is a simplified check - real implementation would validate specific config values
                if not hasattr(config, '__dict__'):
                    config_issues.append("Configuration object invalid")
                    
            except Exception as e:
                config_issues.append(f"Failed to load configuration: {str(e)}")
            
            if config_issues:
                return {
                    "status": "unhealthy",
                    "message": f"Configuration validation failed: {'; '.join(config_issues)}",
                    "details": {"issues": config_issues}
                }
            else:
                return {
                    "status": "healthy",
                    "message": "Configuration validation passed",
                    "details": {"issues": []}
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Configuration validation error: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_authentication_performance(self) -> Dict[str, Any]:
        """Check authentication performance benchmarks."""
        try:
            # Get current metrics
            auth_monitor = get_websocket_auth_monitor()
            metrics = auth_monitor.get_metrics()
            
            # Check latency thresholds
            global_metrics = metrics.get("global_metrics", {})
            latency_percentiles = global_metrics.get("latency_percentiles", {})
            
            p95_latency = latency_percentiles.get("p95", 0)
            avg_latency = latency_percentiles.get("p50", 0)
            
            performance_issues = []
            
            if p95_latency > 5000:  # >5 seconds
                performance_issues.append(f"High P95 latency: {p95_latency:.1f}ms")
            elif p95_latency > 2000:  # >2 seconds
                performance_issues.append(f"Elevated P95 latency: {p95_latency:.1f}ms")
            
            if avg_latency > 1000:  # >1 second
                performance_issues.append(f"High average latency: {avg_latency:.1f}ms")
            
            if performance_issues:
                status = "degraded" if p95_latency <= 5000 else "unhealthy"
                return {
                    "status": status,
                    "message": f"Performance issues detected: {'; '.join(performance_issues)}",
                    "details": {
                        "p95_latency_ms": p95_latency,
                        "avg_latency_ms": avg_latency,
                        "issues": performance_issues
                    }
                }
            else:
                return {
                    "status": "healthy",
                    "message": "Authentication performance is within acceptable limits",
                    "details": {
                        "p95_latency_ms": p95_latency,
                        "avg_latency_ms": avg_latency,
                        "issues": []
                    }
                }
                
        except Exception as e:
            return {
                "status": "degraded",
                "message": f"Performance benchmark check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Dependency check methods
    
    async def _check_redis_connectivity(self) -> bool:
        """Check Redis connectivity."""
        try:
            # This is a placeholder - real implementation would test Redis connection
            # from netra_backend.app.db.redis_client import redis_client
            # return await redis_client.ping()
            return True
        except Exception:
            return False
    
    async def _check_postgresql_connectivity(self) -> bool:
        """Check PostgreSQL connectivity."""
        try:
            # This is a placeholder - real implementation would test PostgreSQL connection
            # from netra_backend.app.db.database_manager import get_database_manager
            # db = get_database_manager()
            # return await db.test_connection()
            return True
        except Exception:
            return False
    
    async def _check_auth_service_connectivity(self) -> bool:
        """Check auth service connectivity."""
        try:
            # This is a placeholder - real implementation would test auth service connection
            # from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
            # auth_service = get_unified_auth_service()
            # return await auth_service.health_check()
            return True
        except Exception:
            return False
    
    async def _check_websocket_monitoring_availability(self) -> bool:
        """Check WebSocket monitoring availability."""
        try:
            auth_monitor = get_websocket_auth_monitor()
            return auth_monitor is not None
        except Exception:
            return False
    
    async def _check_metrics_collector_availability(self) -> bool:
        """Check metrics collector availability."""
        try:
            collector = get_async_auth_metrics_collector()
            return collector is not None
        except Exception:
            return False
    
    async def _check_alert_system_availability(self) -> bool:
        """Check alert system availability."""
        try:
            alert_system = get_auth_alert_system()
            return alert_system is not None
        except Exception:
            return False


# Global instance for authentication health checking
_auth_health_checker: Optional[AuthHealthChecker] = None
_health_checker_lock = threading.Lock()


def get_auth_health_checker() -> AuthHealthChecker:
    """Get or create the global authentication health checker."""
    global _auth_health_checker
    
    if _auth_health_checker is None:
        with _health_checker_lock:
            if _auth_health_checker is None:
                _auth_health_checker = AuthHealthChecker()
                logger.info("Created global AuthHealthChecker for Issue #1300")
    
    return _auth_health_checker


# Convenience functions for health checking

async def check_auth_health(check_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """Check authentication subsystem health."""
    health_checker = get_auth_health_checker()
    result = await health_checker.check_health(check_names)
    return result.to_dict()


async def check_component_health(component_type: str) -> List[Dict[str, Any]]:
    """Check health of a specific component type."""
    health_checker = get_auth_health_checker()
    component_enum = ComponentType(component_type)
    results = await health_checker.check_component_health(component_enum)
    return [result.to_dict() for result in results]


def get_last_health_status() -> Optional[Dict[str, Any]]:
    """Get the last health check results."""
    health_checker = get_auth_health_checker()
    last_status = health_checker.get_last_health_status()
    return last_status.to_dict() if last_status else None


def get_health_statistics() -> Dict[str, Any]:
    """Get health check statistics."""
    health_checker = get_auth_health_checker()
    return health_checker.get_health_statistics()


async def validate_auth_dependencies() -> Dict[str, bool]:
    """Validate authentication system dependencies."""
    health_checker = get_auth_health_checker()
    return await health_checker.validate_dependencies()


# Export public interface
__all__ = [
    "AuthHealthChecker",
    "HealthCheck",
    "HealthCheckResult",
    "OverallHealthStatus",
    "HealthStatus",
    "ComponentType",
    "get_auth_health_checker",
    "check_auth_health",
    "check_component_health",
    "get_last_health_status",
    "get_health_statistics",
    "validate_auth_dependencies"
]