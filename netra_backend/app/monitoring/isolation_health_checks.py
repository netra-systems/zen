"""
Request Isolation Health Checks and Failure Detection

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Proactive detection of isolation violations before they cause system failures
- Value Impact: Prevents cascade failures and ensures 100% service reliability
- Revenue Impact: Critical for Enterprise SLA compliance and customer trust

CRITICAL OBJECTIVES:
1. Detect isolation violations within 30 seconds
2. Trigger immediate alerts for CRITICAL violations  
3. Provide actionable remediation steps
4. Ensure zero silent failures in request isolation
5. Monitor resource leaks and singleton violations
6. Track cross-request state contamination

HEALTH CHECK CATEGORIES:
- Request Isolation: Per-request state isolation integrity
- Factory Performance: Agent instance creation monitoring  
- WebSocket Isolation: Cross-user event contamination detection
- Database Session Isolation: Session leak detection
- Singleton Usage: Detect singleton pattern violations
- Resource Cleanup: Monitor resource leak patterns
"""

import asyncio
import gc
import inspect
import time
import threading
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.isolation_metrics import (
    IsolationMetricsCollector,
    IsolationViolationSeverity,
    get_isolation_metrics_collector
)

logger = central_logger.get_logger(__name__)

class HealthCheckSeverity(Enum):
    """Health check result severity levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    check_name: str
    severity: HealthCheckSeverity
    status: str
    message: str
    timestamp: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)
    remediation_steps: List[str] = field(default_factory=list)
    alert_required: bool = False

@dataclass 
class IsolationHealthStatus:
    """Overall isolation health status."""
    timestamp: datetime
    overall_health: HealthCheckSeverity
    check_results: List[HealthCheckResult]
    isolation_score: float
    failure_containment_rate: float
    critical_violations: int
    active_requests: int
    concurrent_users: int
    system_uptime_hours: float

class IsolationHealthChecker:
    """
    Comprehensive health checker for request isolation system.
    
    CRITICAL: This checker must detect ANY violation of request isolation
    within 30 seconds and trigger immediate alerts. No silent failures allowed.
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize isolation health checker.
        
        Args:
            check_interval: Health check interval in seconds
        """
        self.check_interval = check_interval
        self._lock = threading.Lock()
        
        # Health check state
        self._last_check_time = 0.0
        self._check_history: deque = deque(maxlen=100)
        
        # Instance tracking for singleton detection
        self._tracked_instances: weakref.WeakSet = weakref.WeakSet()
        self._instance_registry: Dict[Type, Set[int]] = defaultdict(set)
        
        # Resource tracking
        self._resource_counts: Dict[str, int] = defaultdict(int)
        self._gc_stats_history: deque = deque(maxlen=50)
        
        # Performance tracking
        self._check_durations: deque = deque(maxlen=100)
        
        # Alert state
        self._last_critical_alert = 0.0
        self._alert_cooldown = 30.0  # seconds
        
        # Background task
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Metrics collector reference
        self._metrics_collector: Optional[IsolationMetricsCollector] = None
        
        logger.info("IsolationHealthChecker initialized")
        
    async def start_health_checks(self) -> None:
        """Start continuous health check monitoring."""
        if self._health_check_task is not None:
            return
            
        self._metrics_collector = get_isolation_metrics_collector()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Isolation health checks started")
        
    async def stop_health_checks(self) -> None:
        """Stop health check monitoring."""
        self._shutdown = True
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Isolation health checks stopped")
        
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while not self._shutdown:
            try:
                start_time = time.time()
                health_status = await self.perform_comprehensive_health_check()
                check_duration = (time.time() - start_time) * 1000  # ms
                
                with self._lock:
                    self._check_durations.append(check_duration)
                    self._check_history.append(health_status)
                    
                # Handle alerts
                await self._process_health_alerts(health_status)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def perform_comprehensive_health_check(self) -> IsolationHealthStatus:
        """Perform comprehensive isolation health check."""
        start_time = time.time()
        check_results = []
        
        try:
            # Run all health checks
            checks = [
                self._check_request_isolation(),
                self._check_singleton_violations(), 
                self._check_websocket_isolation(),
                self._check_database_session_isolation(),
                self._check_resource_leaks(),
                self._check_factory_performance(),
                self._check_concurrent_request_safety(),
                self._check_memory_usage(),
            ]
            
            for check in checks:
                try:
                    result = await check
                    check_results.append(result)
                except Exception as e:
                    error_result = HealthCheckResult(
                        check_name=check.__name__ if hasattr(check, '__name__') else "unknown_check",
                        severity=HealthCheckSeverity.ERROR,
                        status="check_failed",
                        message=f"Health check failed: {str(e)}",
                        timestamp=datetime.now(timezone.utc),
                        alert_required=True
                    )
                    check_results.append(error_result)
                    
            # Determine overall health
            overall_health = self._calculate_overall_health(check_results)
            
            # Get system metrics
            metrics = await self._get_system_metrics()
            
            # Create health status
            health_status = IsolationHealthStatus(
                timestamp=datetime.now(timezone.utc),
                overall_health=overall_health,
                check_results=check_results,
                isolation_score=metrics.get("isolation_score", 100.0),
                failure_containment_rate=metrics.get("failure_containment_rate", 100.0),
                critical_violations=metrics.get("critical_violations", 0),
                active_requests=metrics.get("active_requests", 0),
                concurrent_users=metrics.get("concurrent_users", 0),
                system_uptime_hours=(time.time() - start_time) / 3600
            )
            
            self._last_check_time = time.time()
            return health_status
            
        except Exception as e:
            logger.error(f"Error performing comprehensive health check: {e}")
            # Return error status
            return IsolationHealthStatus(
                timestamp=datetime.now(timezone.utc),
                overall_health=HealthCheckSeverity.CRITICAL,
                check_results=[HealthCheckResult(
                    check_name="comprehensive_check",
                    severity=HealthCheckSeverity.CRITICAL,
                    status="system_error", 
                    message=f"Health check system failure: {str(e)}",
                    timestamp=datetime.now(timezone.utc),
                    alert_required=True
                )],
                isolation_score=0.0,
                failure_containment_rate=0.0,
                critical_violations=999,
                active_requests=0,
                concurrent_users=0,
                system_uptime_hours=0.0
            )
            
    async def _check_request_isolation(self) -> HealthCheckResult:
        """Check overall request isolation status."""
        if not self._metrics_collector:
            return HealthCheckResult(
                check_name="request_isolation",
                severity=HealthCheckSeverity.WARNING,
                status="metrics_unavailable",
                message="Isolation metrics collector not available",
                timestamp=datetime.now(timezone.utc)
            )
            
        isolation_score = self._metrics_collector.get_isolation_score()
        concurrent_users = self._metrics_collector.get_concurrent_users()
        active_requests = self._metrics_collector.get_active_requests()
        
        # Check isolation score
        if isolation_score < 100.0:
            severity = HealthCheckSeverity.CRITICAL
            status = "isolation_compromised"
            message = f"Request isolation compromised: {isolation_score:.1f}% isolation score"
            alert_required = True
            remediation_steps = [
                "Investigate recent isolation violations",
                "Check for singleton pattern usage",
                "Verify factory pattern implementation",
                "Restart affected services if needed"
            ]
        elif concurrent_users > 100:  # High load warning
            severity = HealthCheckSeverity.WARNING
            status = "high_load"
            message = f"High concurrent user load: {concurrent_users} users, {active_requests} active requests"
            alert_required = False
            remediation_steps = [
                "Monitor system resources",
                "Consider scaling if performance degrades",
                "Check request processing times"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "isolated"
            message = f"Request isolation healthy: {isolation_score:.1f}% score, {concurrent_users} users"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="request_isolation",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "isolation_score": isolation_score,
                "concurrent_users": concurrent_users,
                "active_requests": active_requests
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_singleton_violations(self) -> HealthCheckResult:
        """Check for singleton pattern violations."""
        violations = []
        
        # Check for known singleton-prone classes
        singleton_classes = [
            "AgentRegistry",
            "WebSocketManager", 
            "ToolDispatcher"
        ]
        
        for cls_name in singleton_classes:
            # Try to find instances through garbage collection
            for obj in gc.get_objects():
                if hasattr(obj, '__class__') and obj.__class__.__name__ == cls_name:
                    obj_id = id(obj)
                    class_type = type(obj)
                    
                    if class_type in self._instance_registry:
                        if obj_id in self._instance_registry[class_type]:
                            continue  # Already tracked
                        else:
                            # Multiple instances detected
                            violations.append(f"Multiple {cls_name} instances detected")
                    else:
                        self._instance_registry[class_type] = set()
                        
                    self._instance_registry[class_type].add(obj_id)
                    
        # Get violation counts from metrics
        violation_counts = {}
        if self._metrics_collector:
            violation_counts = self._metrics_collector.get_violation_counts()
            
        singleton_violations = violation_counts.get("singleton_reuse", 0)
        
        if singleton_violations > 0 or violations:
            severity = HealthCheckSeverity.ERROR
            status = "violations_detected"
            message = f"Singleton violations detected: {singleton_violations} metric violations, {len(violations)} instance violations"
            alert_required = True
            remediation_steps = [
                "Migrate singleton classes to factory pattern",
                "Ensure proper instance cleanup after requests",
                "Review agent registry implementation",
                "Check WebSocket manager initialization"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "no_violations"
            message = "No singleton violations detected"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="singleton_violations",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "singleton_violations": singleton_violations,
                "instance_violations": len(violations),
                "violation_details": violations
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_websocket_isolation(self) -> HealthCheckResult:
        """Check WebSocket event isolation between users."""
        violation_counts = {}
        if self._metrics_collector:
            violation_counts = self._metrics_collector.get_violation_counts()
            
        websocket_violations = violation_counts.get("websocket_contamination", 0)
        cross_user_events = violation_counts.get("cross_user_events", 0)
        
        # Check WebSocket connection isolation
        try:
            # Try to get WebSocket connection info
            from netra_backend.app.websocket_core.utils import get_connection_monitor
            conn_monitor = get_connection_monitor()
            
            if conn_monitor:
                conn_stats = await conn_monitor.get_stats()
                active_connections = conn_stats.get("active_connections", 0)
            else:
                active_connections = 0
                
        except Exception as e:
            logger.warning(f"Could not get WebSocket connection stats: {e}")
            active_connections = 0
            
        if websocket_violations > 0 or cross_user_events > 0:
            severity = HealthCheckSeverity.CRITICAL
            status = "isolation_violated"
            message = f"WebSocket isolation violations: {websocket_violations} contaminations, {cross_user_events} cross-user events"
            alert_required = True
            remediation_steps = [
                "Investigate WebSocket event routing",
                "Check user context isolation in WebSocket handlers",
                "Verify connection management per user",
                "Restart WebSocket service if needed"
            ]
        elif active_connections > 50:  # High connection count warning
            severity = HealthCheckSeverity.WARNING
            status = "high_connections"
            message = f"High WebSocket connection count: {active_connections} active connections"
            alert_required = False
            remediation_steps = [
                "Monitor connection cleanup",
                "Check for connection leaks",
                "Consider connection limits"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "isolated"
            message = f"WebSocket isolation healthy: {active_connections} connections, no violations"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="websocket_isolation",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "websocket_violations": websocket_violations,
                "cross_user_events": cross_user_events,
                "active_connections": active_connections
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_database_session_isolation(self) -> HealthCheckResult:
        """Check database session isolation and leak detection."""
        violation_counts = {}
        if self._metrics_collector:
            violation_counts = self._metrics_collector.get_violation_counts()
            
        session_leaks = violation_counts.get("db_session_leak", 0)
        shared_sessions = violation_counts.get("shared_db_session", 0)
        
        # Check database connection pool status
        try:
            from netra_backend.app.db.postgres import get_pool_status
            pool_status = get_pool_status()
            
            sync_pool = pool_status.get("sync", {})
            async_pool = pool_status.get("async", {})
            
            total_connections = sync_pool.get("total", 0) + async_pool.get("total", 0)
            pool_size = sync_pool.get("size", 0) + async_pool.get("size", 0)
            pool_overflow = sync_pool.get("overflow", 0) + async_pool.get("overflow", 0)
            
        except Exception as e:
            logger.warning(f"Could not get database pool status: {e}")
            total_connections = 0
            pool_size = 0
            pool_overflow = 0
            
        if session_leaks > 0 or shared_sessions > 0:
            severity = HealthCheckSeverity.ERROR
            status = "session_violations"
            message = f"Database session violations: {session_leaks} leaks, {shared_sessions} shared sessions"
            alert_required = True
            remediation_steps = [
                "Audit database session usage in agents",
                "Ensure sessions are request-scoped only",
                "Check for session cleanup in error handlers",
                "Review database connection patterns"
            ]
        elif pool_overflow > 0:
            severity = HealthCheckSeverity.WARNING
            status = "pool_overflow"
            message = f"Database pool overflow: {pool_overflow} overflow connections"
            alert_required = False
            remediation_steps = [
                "Monitor connection pool usage",
                "Check for connection leaks",
                "Consider increasing pool size",
                "Review long-running queries"
            ]
        elif total_connections > pool_size * 0.9:  # 90% pool utilization
            severity = HealthCheckSeverity.WARNING
            status = "high_utilization"
            message = f"High database pool utilization: {total_connections}/{pool_size} connections"
            alert_required = False
            remediation_steps = [
                "Monitor connection usage patterns",
                "Check for inefficient queries",
                "Consider connection optimization"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "sessions_isolated"
            message = f"Database session isolation healthy: {total_connections}/{pool_size} connections"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="database_session_isolation",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "session_leaks": session_leaks,
                "shared_sessions": shared_sessions,
                "total_connections": total_connections,
                "pool_size": pool_size,
                "pool_overflow": pool_overflow
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_resource_leaks(self) -> HealthCheckResult:
        """Check for resource leaks and cleanup issues."""
        # Collect garbage collection stats
        gc_counts = gc.get_count()
        gc_stats = {
            "gen0": gc_counts[0],
            "gen1": gc_counts[1],
            "gen2": gc_counts[2]
        }
        
        with self._lock:
            self._gc_stats_history.append(gc_stats)
            
        # Check for increasing garbage collection pressure
        if len(self._gc_stats_history) >= 10:
            recent_stats = list(self._gc_stats_history)[-10:]
            avg_gen2 = sum(s["gen2"] for s in recent_stats) / len(recent_stats)
            
            # High gen2 collection pressure indicates potential leaks
            if avg_gen2 > 100:
                severity = HealthCheckSeverity.WARNING
                status = "gc_pressure"
                message = f"High garbage collection pressure: avg {avg_gen2:.1f} gen2 objects"
                alert_required = False
                remediation_steps = [
                    "Monitor memory usage patterns",
                    "Check for circular references",
                    "Review object cleanup in request handlers",
                    "Consider manual garbage collection"
                ]
            else:
                severity = HealthCheckSeverity.HEALTHY
                status = "gc_normal"
                message = f"Normal garbage collection: avg {avg_gen2:.1f} gen2 objects"
                alert_required = False
                remediation_steps = []
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "insufficient_data"
            message = "Insufficient GC data for analysis"
            alert_required = False
            remediation_steps = []
            
        # Check violation counts for resource leaks
        violation_counts = {}
        if self._metrics_collector:
            violation_counts = self._metrics_collector.get_violation_counts()
            
        resource_leaks = violation_counts.get("resource_leak", 0)
        
        if resource_leaks > 0:
            severity = HealthCheckSeverity.ERROR
            status = "leaks_detected"
            message = f"Resource leaks detected: {resource_leaks} violations"
            alert_required = True
            remediation_steps.extend([
                "Investigate specific resource leak violations",
                "Check request cleanup procedures",
                "Audit context manager usage"
            ])
            
        return HealthCheckResult(
            check_name="resource_leaks",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "gc_gen0": gc_stats["gen0"],
                "gc_gen1": gc_stats["gen1"], 
                "gc_gen2": gc_stats["gen2"],
                "resource_leaks": resource_leaks
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_factory_performance(self) -> HealthCheckResult:
        """Check agent factory performance and instance creation times."""
        if not self._metrics_collector:
            return HealthCheckResult(
                check_name="factory_performance",
                severity=HealthCheckSeverity.WARNING,
                status="metrics_unavailable",
                message="Metrics collector unavailable for factory performance check",
                timestamp=datetime.now(timezone.utc)
            )
            
        # Get recent system health
        health = self._metrics_collector.get_current_health()
        
        if health:
            avg_creation_ms = health.avg_instance_creation_ms
            
            if avg_creation_ms > 1000:  # 1 second threshold
                severity = HealthCheckSeverity.CRITICAL
                status = "very_slow"
                message = f"Very slow agent creation: {avg_creation_ms:.1f}ms average"
                alert_required = True
                remediation_steps = [
                    "Investigate factory bottlenecks",
                    "Check for blocking operations in agent initialization",
                    "Consider factory optimizations",
                    "Review agent dependency loading"
                ]
            elif avg_creation_ms > 100:  # 100ms threshold
                severity = HealthCheckSeverity.WARNING
                status = "slow"
                message = f"Slow agent creation: {avg_creation_ms:.1f}ms average"
                alert_required = False
                remediation_steps = [
                    "Monitor factory performance trends",
                    "Check for initialization optimizations",
                    "Review agent startup procedures"
                ]
            else:
                severity = HealthCheckSeverity.HEALTHY
                status = "fast"
                message = f"Fast agent creation: {avg_creation_ms:.1f}ms average"
                alert_required = False
                remediation_steps = []
        else:
            severity = HealthCheckSeverity.WARNING
            status = "no_data"
            message = "No factory performance data available"
            alert_required = False
            remediation_steps = []
            avg_creation_ms = 0.0
            
        return HealthCheckResult(
            check_name="factory_performance",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "avg_creation_ms": avg_creation_ms
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_concurrent_request_safety(self) -> HealthCheckResult:
        """Check safety of concurrent request processing."""
        if not self._metrics_collector:
            return HealthCheckResult(
                check_name="concurrent_request_safety",
                severity=HealthCheckSeverity.WARNING,
                status="metrics_unavailable",
                message="Metrics collector unavailable for concurrent safety check",
                timestamp=datetime.now(timezone.utc)
            )
            
        # Get recent violations
        recent_violations = self._metrics_collector.get_recent_violations(hours=1)
        concurrent_users = self._metrics_collector.get_concurrent_users()
        active_requests = self._metrics_collector.get_active_requests()
        
        # Check for cross-request contamination
        cross_request_violations = [v for v in recent_violations 
                                   if v.violation_type == "cross_request_state"]
        race_condition_violations = [v for v in recent_violations
                                   if v.violation_type == "race_condition"]
        
        if cross_request_violations:
            severity = HealthCheckSeverity.CRITICAL
            status = "contamination_detected"
            message = f"Cross-request state contamination: {len(cross_request_violations)} violations in last hour"
            alert_required = True
            remediation_steps = [
                "IMMEDIATE: Stop processing new requests",
                "Investigate cross-request state sharing",
                "Check for global variable usage",
                "Verify request context isolation",
                "Restart affected services"
            ]
        elif race_condition_violations:
            severity = HealthCheckSeverity.ERROR
            status = "race_conditions"
            message = f"Race condition violations detected: {len(race_condition_violations)} in last hour"
            alert_required = True
            remediation_steps = [
                "Review concurrent access patterns",
                "Check for shared state mutations",
                "Add proper synchronization",
                "Consider request serialization for critical paths"
            ]
        elif concurrent_users > 100 and active_requests > 200:
            severity = HealthCheckSeverity.WARNING
            status = "high_concurrency"
            message = f"High concurrency load: {concurrent_users} users, {active_requests} requests"
            alert_required = False
            remediation_steps = [
                "Monitor system performance under load",
                "Check for resource contention",
                "Consider load balancing",
                "Review concurrent request limits"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "safe"
            message = f"Concurrent request processing safe: {concurrent_users} users, {active_requests} requests"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="concurrent_request_safety",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "cross_request_violations": len(cross_request_violations),
                "race_condition_violations": len(race_condition_violations),
                "concurrent_users": concurrent_users,
                "active_requests": active_requests
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage and trends."""
        import psutil
        
        # Get current memory stats
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        available_gb = memory.available / (1024**3)
        
        # Get process-specific memory
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / (1024**2)
        
        if memory_percent > 90:
            severity = HealthCheckSeverity.CRITICAL
            status = "critical_memory"
            message = f"Critical memory usage: {memory_percent:.1f}% used, {available_gb:.1f}GB available"
            alert_required = True
            remediation_steps = [
                "IMMEDIATE: Check for memory leaks",
                "Consider restarting high memory processes",
                "Review agent cleanup procedures",
                "Monitor garbage collection effectiveness",
                "Scale system resources if needed"
            ]
        elif memory_percent > 75:
            severity = HealthCheckSeverity.WARNING
            status = "high_memory"
            message = f"High memory usage: {memory_percent:.1f}% used, {available_gb:.1f}GB available"
            alert_required = False
            remediation_steps = [
                "Monitor memory usage trends",
                "Check for gradual memory leaks",
                "Review large object allocations",
                "Consider memory optimization"
            ]
        else:
            severity = HealthCheckSeverity.HEALTHY
            status = "normal_memory"
            message = f"Normal memory usage: {memory_percent:.1f}% used, {available_gb:.1f}GB available"
            alert_required = False
            remediation_steps = []
            
        return HealthCheckResult(
            check_name="memory_usage",
            severity=severity,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc),
            metrics={
                "memory_percent": memory_percent,
                "available_gb": available_gb,
                "process_memory_mb": process_memory_mb
            },
            remediation_steps=remediation_steps,
            alert_required=alert_required
        )
        
    def _calculate_overall_health(self, check_results: List[HealthCheckResult]) -> HealthCheckSeverity:
        """Calculate overall health from individual check results."""
        if not check_results:
            return HealthCheckSeverity.HEALTHY
            
        # Find worst severity
        severities = [result.severity for result in check_results]
        
        if HealthCheckSeverity.CRITICAL in severities:
            return HealthCheckSeverity.CRITICAL
        elif HealthCheckSeverity.ERROR in severities:
            return HealthCheckSeverity.ERROR
        elif HealthCheckSeverity.WARNING in severities:
            return HealthCheckSeverity.WARNING
        else:
            return HealthCheckSeverity.HEALTHY
            
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        if not self._metrics_collector:
            return {}
            
        return {
            "isolation_score": self._metrics_collector.get_isolation_score(),
            "failure_containment_rate": self._metrics_collector.get_failure_containment_rate(),
            "concurrent_users": self._metrics_collector.get_concurrent_users(),
            "active_requests": self._metrics_collector.get_active_requests(),
            "critical_violations": len([v for v in self._metrics_collector.get_recent_violations(hours=24) 
                                      if v.severity == IsolationViolationSeverity.CRITICAL])
        }
        
    async def _process_health_alerts(self, health_status: IsolationHealthStatus) -> None:
        """Process health status and trigger alerts if needed."""
        current_time = time.time()
        
        # Check if we need to alert
        needs_alert = (
            health_status.overall_health == HealthCheckSeverity.CRITICAL or
            health_status.critical_violations > 0 or
            any(result.alert_required for result in health_status.check_results)
        )
        
        if needs_alert and (current_time - self._last_critical_alert) > self._alert_cooldown:
            await self._trigger_health_alert(health_status)
            self._last_critical_alert = current_time
            
    async def _trigger_health_alert(self, health_status: IsolationHealthStatus) -> None:
        """Trigger health alert for critical issues."""
        alert_message = f"ISOLATION HEALTH ALERT: {health_status.overall_health.value.upper()}"
        
        # Add details from critical/error checks
        critical_issues = []
        for result in health_status.check_results:
            if result.severity in [HealthCheckSeverity.CRITICAL, HealthCheckSeverity.ERROR]:
                critical_issues.append(f"{result.check_name}: {result.message}")
                
        if critical_issues:
            alert_message += "\n" + "\n".join(critical_issues)
            
        logger.error(alert_message)
        
        # TODO: Integrate with external alerting system
        
    # Public API
    
    async def get_current_health(self) -> Optional[IsolationHealthStatus]:
        """Get current isolation health status."""
        with self._lock:
            return list(self._check_history)[-1] if self._check_history else None
            
    def get_health_history(self, limit: int = 10) -> List[IsolationHealthStatus]:
        """Get recent health check history."""
        with self._lock:
            return list(self._check_history)[-limit:]
            
    async def run_specific_check(self, check_name: str) -> HealthCheckResult:
        """Run a specific health check by name."""
        check_methods = {
            "request_isolation": self._check_request_isolation,
            "singleton_violations": self._check_singleton_violations,
            "websocket_isolation": self._check_websocket_isolation,
            "database_session_isolation": self._check_database_session_isolation,
            "resource_leaks": self._check_resource_leaks,
            "factory_performance": self._check_factory_performance,
            "concurrent_request_safety": self._check_concurrent_request_safety,
            "memory_usage": self._check_memory_usage
        }
        
        if check_name not in check_methods:
            return HealthCheckResult(
                check_name=check_name,
                severity=HealthCheckSeverity.ERROR,
                status="unknown_check",
                message=f"Unknown health check: {check_name}",
                timestamp=datetime.now(timezone.utc)
            )
            
        return await check_methods[check_name]()

# Singleton instance
_isolation_health_checker: Optional[IsolationHealthChecker] = None

def get_isolation_health_checker() -> IsolationHealthChecker:
    """Get or create the global isolation health checker."""
    global _isolation_health_checker
    
    if _isolation_health_checker is None:
        _isolation_health_checker = IsolationHealthChecker()
        
    return _isolation_health_checker

__all__ = [
    'HealthCheckSeverity',
    'HealthCheckResult', 
    'IsolationHealthStatus',
    'IsolationHealthChecker',
    'get_isolation_health_checker'
]