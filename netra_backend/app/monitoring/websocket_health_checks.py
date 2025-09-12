"""
WebSocket Health Checks and Alerting Thresholds System

This module implements comprehensive health checks and automated alerting
for the WebSocket notification system to detect and prevent silent failures.

CRITICAL OBJECTIVES:
1. Provide early warning before users notice issues
2. Enable proactive remediation of degrading systems  
3. Guarantee that notification failures are immediately detected
4. Ensure automated escalation for critical failures

HEALTH CHECK CATEGORIES:
- System Health: Overall notification system status
- User Health: Per-user notification delivery status  
- Bridge Health: WebSocket bridge initialization and connectivity
- Performance Health: Latency and throughput metrics
- Isolation Health: User isolation integrity
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_types import Alert, AlertLevel, NotificationChannel
from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
from netra_backend.app.monitoring.websocket_notification_monitor import (
    WebSocketNotificationMonitor, 
    HealthStatus,
    NotificationEventType
)

logger = central_logger.get_logger(__name__)


class HealthCheckType(Enum):
    """Types of health checks."""
    SYSTEM_OVERALL = "system_overall"
    BRIDGE_INITIALIZATION = "bridge_initialization"
    NOTIFICATION_DELIVERY = "notification_delivery"
    USER_ISOLATION = "user_isolation"
    CONNECTION_STABILITY = "connection_stability"
    PERFORMANCE_METRICS = "performance_metrics"
    SILENT_FAILURE_DETECTION = "silent_failure_detection"
    MEMORY_LEAK_DETECTION = "memory_leak_detection"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    check_type: HealthCheckType
    status: HealthStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metrics
    success_rate: Optional[float] = None
    failure_count: int = 0
    latency_ms: Optional[float] = None
    
    # Issues found
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_healthy(self) -> bool:
        """Check if health check passed."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def requires_immediate_action(self) -> bool:
        """Check if health check requires immediate action."""
        return self.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_type": self.check_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "success_rate": self.success_rate,
            "failure_count": self.failure_count,
            "latency_ms": self.latency_ms,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "is_healthy": self.is_healthy,
            "requires_immediate_action": self.requires_immediate_action
        }


class WebSocketHealthChecker:
    """
    Comprehensive health checking system for WebSocket notifications.
    
    Performs automated health checks to detect:
    - Silent notification failures
    - Bridge initialization problems
    - User isolation violations
    - Performance degradations
    - Connection stability issues
    """
    
    def __init__(self, 
                 monitor: WebSocketNotificationMonitor,
                 alert_manager: NotificationDeliveryManager):
        """Initialize health checker."""
        self.monitor = monitor
        self.alert_manager = alert_manager
        
        # Health check configuration
        self.health_check_interval = 60  # 1 minute
        self.critical_check_interval = 30  # 30 seconds for critical checks
        
        # Thresholds (configurable)
        self.thresholds = {
            "min_success_rate": 0.95,
            "max_silent_failures": 0,
            "max_bridge_failures": 0,
            "max_isolation_violations": 0,
            "max_avg_latency_ms": 1000,
            "max_consecutive_failures": 3,
            "max_memory_growth_mb": 100,
            "min_active_connections": 1
        }
        
        # Health check results history
        self.health_history: Dict[HealthCheckType, List[HealthCheckResult]] = {
            check_type: [] for check_type in HealthCheckType
        }
        self.max_history_per_check = 100
        
        # Background tasks
        self.health_task: Optional[asyncio.Task] = None
        self.critical_check_task: Optional[asyncio.Task] = None
        
        logger.info("[U+1F3E5] WebSocket Health Checker initialized")
    
    async def start_health_monitoring(self) -> None:
        """Start automated health monitoring."""
        if not self.health_task:
            self.health_task = asyncio.create_task(self._health_check_loop())
            logger.info("[U+1F3E5] Health monitoring started")
        
        if not self.critical_check_task:
            self.critical_check_task = asyncio.create_task(self._critical_check_loop())
            logger.info("[U+1F3E5] Critical health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if self.health_task:
            self.health_task.cancel()
            try:
                await self.health_task
            except asyncio.CancelledError:
                pass
            self.health_task = None
        
        if self.critical_check_task:
            self.critical_check_task.cancel()
            try:
                await self.critical_check_task
            except asyncio.CancelledError:
                pass
            self.critical_check_task = None
        
        logger.info("[U+1F3E5] Health monitoring stopped")
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        try:
            while True:
                await self._perform_comprehensive_health_check()
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            logger.info("[U+1F3E5] Health check loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Health check loop error: {e}", exc_info=True)
            await asyncio.sleep(10)  # Brief pause before retrying
    
    async def _critical_check_loop(self) -> None:
        """Critical health check loop for immediate failures."""
        try:
            while True:
                await self._perform_critical_checks()
                await asyncio.sleep(self.critical_check_interval)
                
        except asyncio.CancelledError:
            logger.info("[U+1F3E5] Critical check loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Critical check loop error: {e}", exc_info=True)
            await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _perform_comprehensive_health_check(self) -> Dict[str, HealthCheckResult]:
        """Perform all health checks."""
        results = {}
        
        # Perform all health checks
        check_tasks = [
            self.check_system_health(),
            self.check_bridge_health(), 
            self.check_notification_delivery_health(),
            self.check_user_isolation_health(),
            self.check_connection_stability_health(),
            self.check_performance_health()
        ]
        
        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
            elif isinstance(result, HealthCheckResult):
                results[result.check_type.value] = result
                self._store_health_result(result)
                
                # Send alerts for unhealthy results
                if result.requires_immediate_action:
                    await self._send_health_alert(result)
        
        return results
    
    async def _perform_critical_checks(self) -> None:
        """Perform critical checks for immediate failures."""
        # Check for silent failures
        silent_failure_result = await self.check_silent_failure_health()
        if silent_failure_result.requires_immediate_action:
            await self._send_health_alert(silent_failure_result)
        
        # Check for isolation violations
        isolation_result = await self.check_user_isolation_health()
        if isolation_result.requires_immediate_action:
            await self._send_health_alert(isolation_result)
    
    # Individual health check methods
    
    async def check_system_health(self) -> HealthCheckResult:
        """Check overall system health."""
        system_status = self.monitor.get_system_health_status()
        
        result = HealthCheckResult(
            check_type=HealthCheckType.SYSTEM_OVERALL,
            status=HealthStatus(system_status["status"].value),
            metadata=system_status
        )
        
        # Extract metrics
        system_metrics = system_status.get("system_metrics", {})
        result.success_rate = system_metrics.get("overall_success_rate", 0.0)
        result.failure_count = system_metrics.get("total_notifications_failed", 0)
        
        # Add issues from system status
        result.issues.extend(system_status.get("issues", []))
        
        # Add recommendations based on status
        if result.status == HealthStatus.CRITICAL:
            result.recommendations.extend([
                "Investigate WebSocket bridge initialization",
                "Check for silent notification failures",
                "Verify user isolation integrity"
            ])
        elif result.status == HealthStatus.UNHEALTHY:
            result.recommendations.extend([
                "Monitor notification delivery rates",
                "Check connection stability",
                "Review system performance metrics"
            ])
        
        return result
    
    async def check_bridge_health(self) -> HealthCheckResult:
        """Check WebSocket bridge initialization health."""
        system_metrics = self.monitor.system_metrics
        
        bridge_success_rate = system_metrics.bridge_success_rate
        failed_inits = system_metrics.failed_bridge_initializations
        avg_init_time = system_metrics.avg_bridge_init_time_ms
        
        # Determine status
        if failed_inits > self.thresholds["max_bridge_failures"]:
            status = HealthStatus.CRITICAL
        elif bridge_success_rate < self.thresholds["min_success_rate"]:
            status = HealthStatus.UNHEALTHY
        elif avg_init_time > self.thresholds["max_avg_latency_ms"]:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.BRIDGE_INITIALIZATION,
            status=status,
            success_rate=bridge_success_rate,
            failure_count=failed_inits,
            latency_ms=avg_init_time,
            metadata={
                "total_initializations": system_metrics.total_bridge_initializations,
                "successful_initializations": system_metrics.successful_bridge_initializations
            }
        )
        
        # Add specific issues
        if failed_inits > 0:
            result.issues.append(f"Bridge initialization failures: {failed_inits}")
        if avg_init_time > 1000:
            result.issues.append(f"Slow bridge initialization: {avg_init_time:.1f}ms")
        
        # Add recommendations
        if status != HealthStatus.HEALTHY:
            result.recommendations.extend([
                "Check WebSocket connection pool status",
                "Verify agent registry configuration",
                "Review infrastructure component health"
            ])
        
        return result
    
    async def check_notification_delivery_health(self) -> HealthCheckResult:
        """Check notification delivery health."""
        system_metrics = self.monitor.system_metrics
        
        success_rate = system_metrics.overall_success_rate
        failed_notifications = system_metrics.total_notifications_failed
        avg_delivery_time = system_metrics.avg_notification_delivery_time_ms
        
        # Determine status
        if success_rate < 0.90:
            status = HealthStatus.CRITICAL
        elif success_rate < self.thresholds["min_success_rate"]:
            status = HealthStatus.UNHEALTHY
        elif avg_delivery_time > self.thresholds["max_avg_latency_ms"]:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.NOTIFICATION_DELIVERY,
            status=status,
            success_rate=success_rate,
            failure_count=failed_notifications,
            latency_ms=avg_delivery_time,
            metadata={
                "total_attempted": system_metrics.total_notifications_attempted,
                "total_delivered": system_metrics.total_notifications_delivered
            }
        )
        
        # Add specific issues
        if success_rate < self.thresholds["min_success_rate"]:
            result.issues.append(f"Low notification success rate: {success_rate:.3f}")
        if avg_delivery_time > self.thresholds["max_avg_latency_ms"]:
            result.issues.append(f"High delivery latency: {avg_delivery_time:.1f}ms")
        
        # Add recommendations
        if status != HealthStatus.HEALTHY:
            result.recommendations.extend([
                "Check WebSocket connection quality",
                "Review notification queue status",
                "Analyze delivery failure patterns"
            ])
        
        return result
    
    async def check_silent_failure_health(self) -> HealthCheckResult:
        """Check for silent notification failures."""
        system_metrics = self.monitor.system_metrics
        
        silent_failures = system_metrics.total_silent_failures
        silent_failure_rate = system_metrics.silent_failure_rate
        
        # Determine status - ANY silent failure is critical
        if silent_failures > self.thresholds["max_silent_failures"]:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.SILENT_FAILURE_DETECTION,
            status=status,
            failure_count=silent_failures,
            success_rate=1.0 - silent_failure_rate,
            metadata={
                "silent_failure_rate": silent_failure_rate,
                "detection_window_seconds": self.monitor.silent_failure_detection_window
            }
        )
        
        # Add critical issues
        if silent_failures > 0:
            result.issues.append(f"CRITICAL: {silent_failures} silent failures detected")
            result.issues.append("Users are not receiving notifications without error indication")
        
        # Add urgent recommendations  
        if status == HealthStatus.CRITICAL:
            result.recommendations.extend([
                "IMMEDIATE: Investigate bridge initialization process",
                "IMMEDIATE: Verify WebSocket connection integrity",
                "IMMEDIATE: Check for context propagation failures",
                "IMMEDIATE: Review UnifiedToolExecutionEngine instrumentation"
            ])
        
        return result
    
    async def check_user_isolation_health(self) -> HealthCheckResult:
        """Check user isolation integrity."""
        system_metrics = self.monitor.system_metrics
        
        isolation_violations = system_metrics.user_isolation_violations
        cross_user_events = system_metrics.cross_user_events
        
        # Determine status - ANY isolation violation is critical
        if isolation_violations > self.thresholds["max_isolation_violations"]:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.USER_ISOLATION,
            status=status,
            failure_count=isolation_violations,
            metadata={
                "cross_user_events": cross_user_events,
                "active_users": len(self.monitor.user_metrics)
            }
        )
        
        # Add critical issues
        if isolation_violations > 0:
            result.issues.append(f"CRITICAL: {isolation_violations} user isolation violations")
            result.issues.append("User notifications may be sent to wrong recipients")
        
        if cross_user_events > 0:
            result.warnings.append(f"Cross-user events detected: {cross_user_events}")
        
        # Add urgent recommendations
        if status == HealthStatus.CRITICAL:
            result.recommendations.extend([
                "IMMEDIATE: Audit user context propagation",
                "IMMEDIATE: Verify per-user WebSocket bridge isolation",
                "IMMEDIATE: Check for shared state contamination",
                "IMMEDIATE: Review factory pattern implementation"
            ])
        
        return result
    
    async def check_connection_stability_health(self) -> HealthCheckResult:
        """Check WebSocket connection stability."""
        system_metrics = self.monitor.system_metrics
        
        connection_drops = system_metrics.total_connection_drops
        reconnections = system_metrics.total_reconnections
        active_connections = system_metrics.active_connections
        
        # Calculate stability metrics
        if reconnections > 0:
            drop_rate = connection_drops / reconnections
        else:
            drop_rate = 0.0
        
        # Determine status
        if active_connections < self.thresholds["min_active_connections"]:
            status = HealthStatus.CRITICAL
        elif drop_rate > 0.1:  # More than 10% drop rate
            status = HealthStatus.UNHEALTHY
        elif drop_rate > 0.05:  # More than 5% drop rate
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.CONNECTION_STABILITY,
            status=status,
            failure_count=connection_drops,
            metadata={
                "drop_rate": drop_rate,
                "total_reconnections": reconnections,
                "active_connections": active_connections
            }
        )
        
        # Add issues
        if active_connections == 0:
            result.issues.append("CRITICAL: No active WebSocket connections")
        elif active_connections < self.thresholds["min_active_connections"]:
            result.issues.append(f"Low active connections: {active_connections}")
            
        if drop_rate > 0.1:
            result.issues.append(f"High connection drop rate: {drop_rate:.1%}")
        
        # Add recommendations
        if status != HealthStatus.HEALTHY:
            result.recommendations.extend([
                "Check network connectivity",
                "Review WebSocket keepalive settings",
                "Analyze connection drop patterns",
                "Consider connection pooling improvements"
            ])
        
        return result
    
    async def check_performance_health(self) -> HealthCheckResult:
        """Check performance metrics health."""
        system_metrics = self.monitor.system_metrics
        performance_metrics = self.monitor.get_performance_metrics()
        
        avg_delivery_time = system_metrics.avg_notification_delivery_time_ms
        avg_bridge_init_time = system_metrics.avg_bridge_init_time_ms
        memory_samples = performance_metrics.get("performance_samples", [])
        
        # Determine status
        if avg_delivery_time > 5000:  # 5 seconds
            status = HealthStatus.CRITICAL
        elif avg_delivery_time > self.thresholds["max_avg_latency_ms"]:
            status = HealthStatus.UNHEALTHY
        elif avg_bridge_init_time > 1000:  # 1 second
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.PERFORMANCE_METRICS,
            status=status,
            latency_ms=avg_delivery_time,
            metadata={
                "avg_bridge_init_time_ms": avg_bridge_init_time,
                "memory_samples_count": len(memory_samples),
                "performance_baseline": performance_metrics.get("memory_baseline_mb")
            }
        )
        
        # Add performance issues
        if avg_delivery_time > 5000:
            result.issues.append(f"CRITICAL: Very high notification latency: {avg_delivery_time:.1f}ms")
        elif avg_delivery_time > self.thresholds["max_avg_latency_ms"]:
            result.issues.append(f"High notification latency: {avg_delivery_time:.1f}ms")
        
        if avg_bridge_init_time > 1000:
            result.issues.append(f"Slow bridge initialization: {avg_bridge_init_time:.1f}ms")
        
        # Check for memory trends
        if len(memory_samples) >= 2:
            recent_memory = memory_samples[-1].get("memory_mb", 0)
            baseline_memory = memory_samples[0].get("memory_mb", 0)
            memory_growth = recent_memory - baseline_memory
            
            if memory_growth > self.thresholds["max_memory_growth_mb"]:
                result.warnings.append(f"Memory growth detected: +{memory_growth:.1f}MB")
        
        # Add recommendations
        if status != HealthStatus.HEALTHY:
            result.recommendations.extend([
                "Analyze notification delivery bottlenecks",
                "Review WebSocket message processing efficiency", 
                "Consider connection pooling optimizations",
                "Monitor memory usage trends"
            ])
        
        return result
    
    async def check_memory_leak_health(self) -> HealthCheckResult:
        """Check for memory leaks in WebSocket system."""
        system_metrics = self.monitor.system_metrics
        memory_leaks = system_metrics.memory_leaks_detected
        
        status = HealthStatus.CRITICAL if memory_leaks > 0 else HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.MEMORY_LEAK_DETECTION,
            status=status,
            failure_count=memory_leaks,
            metadata={"memory_leaks_detected": memory_leaks}
        )
        
        if memory_leaks > 0:
            result.issues.append(f"Memory leaks detected: {memory_leaks}")
            result.recommendations.extend([
                "IMMEDIATE: Review WebSocket connection cleanup",
                "IMMEDIATE: Check for unreleased resources",
                "IMMEDIATE: Audit event queue management"
            ])
        
        return result
    
    # User-specific health checks
    
    async def check_user_health(self, user_id: str) -> Optional[HealthCheckResult]:
        """Check health for specific user."""
        user_metrics_data = self.monitor.get_user_metrics(user_id)
        
        if not user_metrics_data:
            return None
        
        # Aggregate metrics across all user sessions
        total_attempted = sum(m["notifications_attempted"] for m in user_metrics_data.values())
        total_delivered = sum(m["notifications_delivered"] for m in user_metrics_data.values())
        total_failed = sum(m["notifications_failed"] for m in user_metrics_data.values()) 
        total_silent = sum(m["silent_failures"] for m in user_metrics_data.values())
        max_consecutive = max((m["consecutive_failures"] for m in user_metrics_data.values()), default=0)
        
        success_rate = total_delivered / total_attempted if total_attempted > 0 else 1.0
        
        # Determine user health status
        if total_silent > 0 or max_consecutive >= 5:
            status = HealthStatus.CRITICAL
        elif success_rate < 0.90 or max_consecutive >= 3:
            status = HealthStatus.UNHEALTHY
        elif success_rate < 0.95:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        result = HealthCheckResult(
            check_type=HealthCheckType.NOTIFICATION_DELIVERY,
            status=status,
            success_rate=success_rate,
            failure_count=total_failed,
            metadata={
                "user_id": user_id,
                "total_sessions": len(user_metrics_data),
                "silent_failures": total_silent,
                "consecutive_failures": max_consecutive
            }
        )
        
        # Add user-specific issues
        if total_silent > 0:
            result.issues.append(f"CRITICAL: User has {total_silent} silent failures")
        if max_consecutive >= 3:
            result.issues.append(f"High consecutive failures: {max_consecutive}")
        if success_rate < 0.95:
            result.issues.append(f"Low user success rate: {success_rate:.3f}")
        
        return result
    
    # Alert management
    
    async def _send_health_alert(self, health_result: HealthCheckResult) -> None:
        """Send health alert based on check result."""
        # Determine alert level
        if health_result.status == HealthStatus.CRITICAL:
            alert_level = AlertLevel.CRITICAL
        elif health_result.status == HealthStatus.UNHEALTHY:
            alert_level = AlertLevel.ERROR
        else:
            alert_level = AlertLevel.WARNING
        
        # Create alert
        alert = Alert(
            title=f"WebSocket Health Alert: {health_result.check_type.value}",
            message=self._format_health_alert_message(health_result),
            level=alert_level,
            component="websocket_health_checker",
            agent_name="HealthMonitor",
            metadata={
                "check_type": health_result.check_type.value,
                "health_status": health_result.status.value,
                "issues": health_result.issues,
                "recommendations": health_result.recommendations,
                "metrics": {
                    "success_rate": health_result.success_rate,
                    "failure_count": health_result.failure_count,
                    "latency_ms": health_result.latency_ms
                }
            }
        )
        
        # Send alert
        try:
            channels = [NotificationChannel.LOG, NotificationChannel.DATABASE]
            await self.alert_manager.deliver_notifications(alert, channels, {})
            logger.info(f" ALERT:  Health alert sent: {health_result.check_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    def _format_health_alert_message(self, health_result: HealthCheckResult) -> str:
        """Format health alert message."""
        message_parts = [
            f"Health check failed: {health_result.check_type.value}",
            f"Status: {health_result.status.value}",
        ]
        
        if health_result.success_rate is not None:
            message_parts.append(f"Success rate: {health_result.success_rate:.3f}")
        
        if health_result.failure_count > 0:
            message_parts.append(f"Failures: {health_result.failure_count}")
        
        if health_result.latency_ms is not None:
            message_parts.append(f"Latency: {health_result.latency_ms:.1f}ms")
        
        if health_result.issues:
            message_parts.append(f"Issues: {'; '.join(health_result.issues)}")
        
        return " | ".join(message_parts)
    
    def _store_health_result(self, result: HealthCheckResult) -> None:
        """Store health check result in history."""
        check_history = self.health_history[result.check_type]
        check_history.append(result)
        
        # Trim history to max size
        if len(check_history) > self.max_history_per_check:
            check_history[:] = check_history[-self.max_history_per_check:]
    
    # Public API methods
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        latest_results = {}
        overall_status = HealthStatus.HEALTHY
        critical_issues = []
        
        # Get latest result for each check type
        for check_type, history in self.health_history.items():
            if history:
                latest = history[-1]
                latest_results[check_type.value] = latest.to_dict()
                
                # Determine overall status (worst case)
                if latest.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                    critical_issues.extend(latest.issues)
                elif latest.status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.UNHEALTHY
                elif latest.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical_issues": critical_issues,
            "health_checks": latest_results,
            "monitoring_active": self.health_task is not None and not self.health_task.done()
        }
    
    def get_health_trends(self, check_type: HealthCheckType, hours: int = 24) -> Dict[str, Any]:
        """Get health trends for a specific check type."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        history = self.health_history.get(check_type, [])
        recent_results = [r for r in history if r.timestamp > cutoff_time]
        
        if not recent_results:
            return {"check_type": check_type.value, "trend_data": []}
        
        trend_data = []
        for result in recent_results:
            trend_data.append({
                "timestamp": result.timestamp.isoformat(),
                "status": result.status.value,
                "success_rate": result.success_rate,
                "failure_count": result.failure_count,
                "latency_ms": result.latency_ms
            })
        
        # Calculate trend statistics
        success_rates = [r.success_rate for r in recent_results if r.success_rate is not None]
        latencies = [r.latency_ms for r in recent_results if r.latency_ms is not None]
        
        stats = {
            "check_type": check_type.value,
            "trend_data": trend_data,
            "period_hours": hours,
            "total_checks": len(recent_results),
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else None,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "health_deteriorating": self._is_health_deteriorating(recent_results)
        }
        
        return stats
    
    def _is_health_deteriorating(self, results: List[HealthCheckResult]) -> bool:
        """Check if health is deteriorating over time."""
        if len(results) < 3:
            return False
        
        # Check if recent results are worse than earlier results
        recent_third = results[-len(results)//3:]
        earlier_third = results[:len(results)//3]
        
        recent_unhealthy = sum(1 for r in recent_third if r.status != HealthStatus.HEALTHY)
        earlier_unhealthy = sum(1 for r in earlier_third if r.status != HealthStatus.HEALTHY)
        
        recent_unhealthy_rate = recent_unhealthy / len(recent_third)
        earlier_unhealthy_rate = earlier_unhealthy / len(earlier_third) if earlier_third else 0
        
        return recent_unhealthy_rate > earlier_unhealthy_rate
    
    # Emergency health checks
    
    async def emergency_health_assessment(self) -> Dict[str, Any]:
        """Perform emergency health assessment for critical issues."""
        logger.critical(" ALERT:  EMERGENCY HEALTH ASSESSMENT: Performing critical system checks")
        
        # Perform all critical checks immediately
        critical_results = await asyncio.gather(
            self.check_silent_failure_health(),
            self.check_user_isolation_health(),
            self.check_bridge_health(),
            return_exceptions=True
        )
        
        critical_issues = []
        emergency_actions = []
        
        for result in critical_results:
            if isinstance(result, Exception):
                critical_issues.append(f"Health check failed: {result}")
                continue
            
            if result.status == HealthStatus.CRITICAL:
                critical_issues.extend(result.issues)
                emergency_actions.extend(result.recommendations)
        
        assessment = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emergency_triggered": True,
            "critical_issues_found": len(critical_issues),
            "critical_issues": critical_issues,
            "emergency_actions": emergency_actions,
            "system_requires_immediate_attention": len(critical_issues) > 0
        }
        
        # Log emergency assessment
        if critical_issues:
            logger.critical(f" ALERT:  EMERGENCY ASSESSMENT: {len(critical_issues)} critical issues found")
            for issue in critical_issues:
                logger.critical(f" ALERT:  CRITICAL ISSUE: {issue}")
        else:
            logger.info("[U+1F3E5] Emergency assessment: No critical issues detected")
        
        return assessment


# Global health checker instance
_websocket_health_checker: Optional[WebSocketHealthChecker] = None


def get_websocket_health_checker() -> WebSocketHealthChecker:
    """Get or create the global WebSocket health checker."""
    global _websocket_health_checker
    if _websocket_health_checker is None:
        from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
        from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
        
        monitor = get_websocket_notification_monitor()
        alert_manager = NotificationDeliveryManager()
        _websocket_health_checker = WebSocketHealthChecker(monitor, alert_manager)
    
    return _websocket_health_checker


async def start_websocket_health_monitoring() -> None:
    """Start global WebSocket health monitoring."""
    health_checker = get_websocket_health_checker()
    await health_checker.start_health_monitoring()
    logger.info("[U+1F3E5] Global WebSocket health monitoring started")


async def stop_websocket_health_monitoring() -> None:
    """Stop global WebSocket health monitoring."""
    global _websocket_health_checker
    if _websocket_health_checker:
        await _websocket_health_checker.stop_health_monitoring()
        logger.info("[U+1F3E5] Global WebSocket health monitoring stopped")


async def perform_emergency_health_check() -> Dict[str, Any]:
    """Perform emergency health check and return assessment."""
    health_checker = get_websocket_health_checker()
    return await health_checker.emergency_health_assessment()