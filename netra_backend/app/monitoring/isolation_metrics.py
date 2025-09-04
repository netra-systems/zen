"""
Request Isolation Metrics Collection and Monitoring

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: System reliability through complete request isolation
- Value Impact: Prevents cascade failures, ensures 100% service availability
- Revenue Impact: Critical for Enterprise SLA guarantees and customer trust

CRITICAL: This module provides real-time monitoring of request isolation
to ensure ZERO FAILURE PROPAGATION between user requests.

Metrics Collected:
- isolation_score: % of properly isolated requests (TARGET: 100%)
- failure_containment_rate: % failures that don't cascade 
- instance_creation_time_ms: Factory performance monitoring
- websocket_isolation_violations: Cross-user event contamination
- session_leak_count: Database session leaks per request
- concurrent_users: Real-time active user count
- request_isolation_status: Per-request isolation tracking
"""

import asyncio
import time
import threading
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Alert severity levels for isolation violations
class IsolationViolationSeverity(Enum):
    """Severity levels for isolation violations."""
    CRITICAL = "critical"     # Cross-request state contamination
    ERROR = "error"           # Singleton instance reused  
    WARNING = "warning"       # Performance degradation
    INFO = "info"            # Normal operations

@dataclass
class IsolationViolation:
    """Record of an isolation violation."""
    timestamp: datetime
    violation_type: str
    severity: IsolationViolationSeverity
    user_id: Optional[str]
    request_id: Optional[str]
    description: str
    stack_trace: Optional[str] = None
    remediation_attempted: bool = False
    
@dataclass
class RequestIsolationMetrics:
    """Metrics for a single request's isolation status."""
    request_id: str
    user_id: str
    thread_id: Optional[str]
    run_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    instance_creation_time_ms: float = 0.0
    websocket_isolated: bool = True
    db_session_isolated: bool = True
    agent_instance_isolated: bool = True
    state_isolated: bool = True
    failure_contained: bool = True
    isolation_score: float = 100.0  # Percentage 0-100
    violations: List[IsolationViolation] = field(default_factory=list)

@dataclass  
class SystemIsolationHealth:
    """Overall system isolation health status."""
    timestamp: datetime
    total_requests: int
    isolated_requests: int
    isolation_score: float  # Percentage of properly isolated requests
    failure_containment_rate: float  # Percentage of failures contained
    concurrent_users: int
    active_websocket_connections: int
    singleton_violations: int
    cross_request_contamination: int
    resource_leaks: int
    avg_instance_creation_ms: float
    critical_violations_24h: int
    system_status: IsolationViolationSeverity

class IsolationMetricsCollector:
    """
    Collects and monitors request isolation metrics to ensure zero failure propagation.
    
    CRITICAL: This collector must detect ANY violation of request isolation
    immediately and trigger alerts. Silent failures are unacceptable.
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize isolation metrics collector.
        
        Args:
            retention_hours: How long to retain metrics history
        """
        self.retention_hours = retention_hours
        self._lock = threading.Lock()
        
        # Active request tracking
        self._active_requests: Dict[str, RequestIsolationMetrics] = {}
        self._completed_requests: deque = deque(maxlen=10000)
        
        # Isolation violation tracking
        self._violations: deque = deque(maxlen=1000)  
        self._violation_counts: Dict[str, int] = defaultdict(int)
        
        # System health tracking
        self._health_history: deque = deque(maxlen=1440)  # 24h of minute samples
        
        # Performance metrics
        self._instance_creation_times: deque = deque(maxlen=1000)
        self._websocket_isolation_checks: deque = deque(maxlen=1000)
        
        # User session tracking
        self._active_users: Set[str] = set()
        self._user_request_counts: Dict[str, int] = defaultdict(int)
        
        # Alert state
        self._last_critical_alert = 0.0
        self._alert_cooldown = 30.0  # seconds
        
        # Collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info("IsolationMetricsCollector initialized")
        
    async def start_collection(self) -> None:
        """Start metrics collection background task."""
        if self._collection_task is not None:
            return
            
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Isolation metrics collection started")
        
    async def stop_collection(self) -> None:
        """Stop metrics collection."""
        self._shutdown = True
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Isolation metrics collection stopped")
        
    async def _collection_loop(self) -> None:
        """Background collection and health check loop."""
        while not self._shutdown:
            try:
                await self._collect_system_health()
                await self._check_isolation_violations()
                await self._cleanup_expired_data()
                await asyncio.sleep(5.0)  # Collect every 5 seconds
            except Exception as e:
                logger.error(f"Error in isolation metrics collection loop: {e}")
                await asyncio.sleep(5.0)
                
    async def _collect_system_health(self) -> None:
        """Collect overall system isolation health metrics."""
        with self._lock:
            now = datetime.now(timezone.utc)
            
            # Calculate isolation scores
            total_requests = len(self._completed_requests)
            if total_requests > 0:
                isolated_requests = sum(1 for req in self._completed_requests 
                                      if req.isolation_score == 100.0)
                isolation_score = (isolated_requests / total_requests) * 100
                
                # Calculate failure containment rate
                failed_requests = sum(1 for req in self._completed_requests 
                                    if not req.failure_contained)
                failure_containment_rate = ((total_requests - failed_requests) / total_requests) * 100
            else:
                isolation_score = 100.0
                failure_containment_rate = 100.0
                
            # Get current resource usage
            concurrent_users = len(self._active_users)
            active_requests = len(self._active_requests)
            
            # Calculate violation counts
            recent_violations = [v for v in self._violations 
                               if (now - v.timestamp).total_seconds() < 3600]  # Last hour
            critical_violations_24h = sum(1 for v in self._violations 
                                        if (now - v.timestamp).total_seconds() < 86400 and 
                                        v.severity == IsolationViolationSeverity.CRITICAL)
                                        
            # Average instance creation time
            if self._instance_creation_times:
                avg_creation_ms = sum(self._instance_creation_times) / len(self._instance_creation_times)
            else:
                avg_creation_ms = 0.0
                
            # Determine system status
            if critical_violations_24h > 0 or isolation_score < 100.0:
                system_status = IsolationViolationSeverity.CRITICAL
            elif len(recent_violations) > 10:
                system_status = IsolationViolationSeverity.ERROR
            elif avg_creation_ms > 100:  # Slow instance creation
                system_status = IsolationViolationSeverity.WARNING
            else:
                system_status = IsolationViolationSeverity.INFO
                
            # Create health record
            health = SystemIsolationHealth(
                timestamp=now,
                total_requests=total_requests,
                isolated_requests=isolated_requests if total_requests > 0 else 0,
                isolation_score=isolation_score,
                failure_containment_rate=failure_containment_rate,
                concurrent_users=concurrent_users,
                active_websocket_connections=active_requests,  # Approximation
                singleton_violations=self._violation_counts.get("singleton_reuse", 0),
                cross_request_contamination=self._violation_counts.get("cross_request_state", 0),
                resource_leaks=self._violation_counts.get("resource_leak", 0),
                avg_instance_creation_ms=avg_creation_ms,
                critical_violations_24h=critical_violations_24h,
                system_status=system_status
            )
            
            self._health_history.append(health)
            
            # Trigger alerts if needed
            await self._check_alert_conditions(health)
            
    async def _check_isolation_violations(self) -> None:
        """Check for active isolation violations."""
        current_time = time.time()
        
        with self._lock:
            # Check for long-running requests (potential resource leaks)
            for request_id, metrics in list(self._active_requests.items()):
                request_age = (datetime.now(timezone.utc) - metrics.start_time).total_seconds()
                
                if request_age > 300:  # 5 minutes
                    await self._record_violation(
                        "long_running_request",
                        IsolationViolationSeverity.WARNING,
                        metrics.user_id,
                        request_id,
                        f"Request running for {request_age:.1f} seconds, potential resource leak"
                    )
                    
            # Check for too many concurrent users (system overload)
            if len(self._active_users) > 50:  # Configurable threshold
                await self._record_violation(
                    "high_concurrent_users",
                    IsolationViolationSeverity.WARNING,
                    None,
                    None,
                    f"High concurrent user count: {len(self._active_users)}"
                )
                
    async def _check_alert_conditions(self, health: SystemIsolationHealth) -> None:
        """Check if alert conditions are met and trigger alerts."""
        current_time = time.time()
        should_alert = False
        alert_message = ""
        
        # CRITICAL: isolation_score < 100%
        if health.isolation_score < 100.0:
            should_alert = True
            alert_message = f"CRITICAL: Request isolation compromised - {health.isolation_score:.1f}% isolated"
            
        # CRITICAL: Cross-request state contamination detected
        elif health.cross_request_contamination > 0:
            should_alert = True
            alert_message = f"CRITICAL: Cross-request state contamination detected - {health.cross_request_contamination} violations"
            
        # ERROR: Singleton instance reused
        elif health.singleton_violations > 0:
            should_alert = True
            alert_message = f"ERROR: Singleton instances reused across requests - {health.singleton_violations} violations"
            
        # WARNING: Slow instance creation
        elif health.avg_instance_creation_ms > 100:
            should_alert = True  
            alert_message = f"WARNING: Slow agent instance creation - {health.avg_instance_creation_ms:.1f}ms average"
            
        if should_alert and (current_time - self._last_critical_alert) > self._alert_cooldown:
            await self._trigger_alert(alert_message, health)
            self._last_critical_alert = current_time
            
    async def _trigger_alert(self, message: str, health: SystemIsolationHealth) -> None:
        """Trigger isolation violation alert."""
        logger.error(f"ISOLATION ALERT: {message}")
        
        # Additional detailed logging for debugging
        logger.error(f"System Health Details: "
                    f"isolation_score={health.isolation_score:.1f}%, "
                    f"concurrent_users={health.concurrent_users}, "
                    f"violations_24h={health.critical_violations_24h}")
                    
        # TODO: Integrate with external alerting system (PagerDuty, Slack, etc.)
        
    async def _cleanup_expired_data(self) -> None:
        """Clean up expired metrics data."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean violations
            expired_violations = []
            for i, violation in enumerate(self._violations):
                if violation.timestamp < cutoff_time:
                    expired_violations.append(i)
                    
            for i in reversed(expired_violations):
                del self._violations[i]
                
            # Clean completed requests (deque handles this automatically with maxlen)
            # Clean health history (deque handles this automatically with maxlen)
            
    # Public API Methods
    
    def start_request(self, user_id: str, request_id: str, 
                     thread_id: Optional[str] = None, 
                     run_id: Optional[str] = None) -> None:
        """Start tracking a new request."""
        with self._lock:
            metrics = RequestIsolationMetrics(
                request_id=request_id,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                start_time=datetime.now(timezone.utc)
            )
            
            self._active_requests[request_id] = metrics
            self._active_users.add(user_id)
            self._user_request_counts[user_id] += 1
            
        logger.debug(f"Started tracking request {request_id} for user {user_id}")
        
    def complete_request(self, request_id: str, success: bool = True) -> None:
        """Complete tracking a request."""
        with self._lock:
            if request_id not in self._active_requests:
                logger.warning(f"Attempted to complete unknown request: {request_id}")
                return
                
            metrics = self._active_requests.pop(request_id)
            metrics.end_time = datetime.now(timezone.utc)
            metrics.failure_contained = success
            
            # Calculate final isolation score
            metrics.isolation_score = self._calculate_isolation_score(metrics)
            
            self._completed_requests.append(metrics)
            
            # Update user tracking
            self._user_request_counts[metrics.user_id] -= 1
            if self._user_request_counts[metrics.user_id] <= 0:
                self._active_users.discard(metrics.user_id)
                del self._user_request_counts[metrics.user_id]
                
        logger.debug(f"Completed tracking request {request_id}, isolation_score={metrics.isolation_score:.1f}%")
        
    def record_instance_creation_time(self, request_id: str, creation_time_ms: float) -> None:
        """Record agent instance creation time."""
        with self._lock:
            self._instance_creation_times.append(creation_time_ms)
            
            if request_id in self._active_requests:
                self._active_requests[request_id].instance_creation_time_ms = creation_time_ms
                
            # Check for slow creation (potential performance issue)
            if creation_time_ms > 100:  # 100ms threshold
                asyncio.create_task(self._record_violation(
                    "slow_instance_creation",
                    IsolationViolationSeverity.WARNING,
                    self._active_requests.get(request_id, {}).user_id if request_id in self._active_requests else None,
                    request_id,
                    f"Slow agent instance creation: {creation_time_ms:.1f}ms"
                ))
                
        logger.debug(f"Recorded instance creation time: {creation_time_ms:.1f}ms for request {request_id}")
        
    async def record_isolation_violation(self, violation_type: str, 
                                       severity: IsolationViolationSeverity,
                                       request_id: Optional[str] = None,
                                       user_id: Optional[str] = None,
                                       description: str = "") -> None:
        """Record an isolation violation."""
        await self._record_violation(violation_type, severity, user_id, request_id, description)
        
        # Update request metrics if available
        with self._lock:
            if request_id and request_id in self._active_requests:
                metrics = self._active_requests[request_id]
                
                # Update isolation flags based on violation type
                if violation_type == "websocket_contamination":
                    metrics.websocket_isolated = False
                elif violation_type == "db_session_leak":
                    metrics.db_session_isolated = False
                elif violation_type == "singleton_reuse":
                    metrics.agent_instance_isolated = False
                elif violation_type == "cross_request_state":
                    metrics.state_isolated = False
                    
    async def _record_violation(self, violation_type: str, 
                              severity: IsolationViolationSeverity,
                              user_id: Optional[str],
                              request_id: Optional[str],
                              description: str) -> None:
        """Internal method to record violation."""
        violation = IsolationViolation(
            timestamp=datetime.now(timezone.utc),
            violation_type=violation_type,
            severity=severity,
            user_id=user_id,
            request_id=request_id,
            description=description,
            stack_trace=traceback.format_stack() if severity == IsolationViolationSeverity.CRITICAL else None
        )
        
        with self._lock:
            self._violations.append(violation)
            self._violation_counts[violation_type] += 1
            
        # Log violation with appropriate level
        log_msg = f"ISOLATION VIOLATION [{violation_type}]: {description}"
        if severity == IsolationViolationSeverity.CRITICAL:
            logger.error(log_msg)
        elif severity == IsolationViolationSeverity.ERROR:
            logger.error(log_msg)
        elif severity == IsolationViolationSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
    def _calculate_isolation_score(self, metrics: RequestIsolationMetrics) -> float:
        """Calculate isolation score for a request (0-100%)."""
        score = 100.0
        
        # Deduct points for each isolation failure
        if not metrics.websocket_isolated:
            score -= 25.0
        if not metrics.db_session_isolated:
            score -= 25.0
        if not metrics.agent_instance_isolated:
            score -= 25.0
        if not metrics.state_isolated:
            score -= 25.0
            
        # Additional deductions for violations
        for violation in metrics.violations:
            if violation.severity == IsolationViolationSeverity.CRITICAL:
                score -= 50.0
            elif violation.severity == IsolationViolationSeverity.ERROR:
                score -= 25.0
            elif violation.severity == IsolationViolationSeverity.WARNING:
                score -= 10.0
                
        return max(0.0, score)
        
    # Metrics API
    
    def get_current_health(self) -> Optional[SystemIsolationHealth]:
        """Get current system isolation health."""
        with self._lock:
            return list(self._health_history)[-1] if self._health_history else None
            
    def get_isolation_score(self) -> float:
        """Get current isolation score (0-100%)."""
        health = self.get_current_health()
        return health.isolation_score if health else 100.0
        
    def get_failure_containment_rate(self) -> float:
        """Get current failure containment rate (0-100%)."""
        health = self.get_current_health()
        return health.failure_containment_rate if health else 100.0
        
    def get_concurrent_users(self) -> int:
        """Get current concurrent user count."""
        with self._lock:
            return len(self._active_users)
            
    def get_active_requests(self) -> int:
        """Get current active request count."""
        with self._lock:
            return len(self._active_requests)
            
    def get_recent_violations(self, hours: int = 1) -> List[IsolationViolation]:
        """Get recent isolation violations."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._lock:
            return [v for v in self._violations if v.timestamp >= cutoff_time]
            
    def get_violation_counts(self) -> Dict[str, int]:
        """Get violation counts by type."""
        with self._lock:
            return dict(self._violation_counts)
            
    def get_health_history(self, hours: int = 24) -> List[SystemIsolationHealth]:
        """Get system health history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._lock:
            return [h for h in self._health_history if h.timestamp >= cutoff_time]
            

# Singleton instance for global access
_isolation_metrics_collector: Optional[IsolationMetricsCollector] = None

def get_isolation_metrics_collector() -> IsolationMetricsCollector:
    """Get or create the global isolation metrics collector."""
    global _isolation_metrics_collector
    
    if _isolation_metrics_collector is None:
        _isolation_metrics_collector = IsolationMetricsCollector()
        
    return _isolation_metrics_collector

# Convenience functions for easy integration
async def start_request_tracking(user_id: str, request_id: str, 
                               thread_id: Optional[str] = None,
                               run_id: Optional[str] = None) -> None:
    """Start tracking request isolation."""
    collector = get_isolation_metrics_collector()
    collector.start_request(user_id, request_id, thread_id, run_id)
    
async def complete_request_tracking(request_id: str, success: bool = True) -> None:
    """Complete request isolation tracking."""
    collector = get_isolation_metrics_collector()
    collector.complete_request(request_id, success)
    
async def record_instance_creation_time(request_id: str, creation_time_ms: float) -> None:
    """Record agent instance creation time."""
    collector = get_isolation_metrics_collector()
    collector.record_instance_creation_time(request_id, creation_time_ms)
    
async def record_violation(violation_type: str, 
                         severity: IsolationViolationSeverity,
                         request_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         description: str = "") -> None:
    """Record an isolation violation."""
    collector = get_isolation_metrics_collector()
    await collector.record_isolation_violation(violation_type, severity, request_id, user_id, description)

__all__ = [
    'IsolationViolationSeverity',
    'IsolationViolation', 
    'RequestIsolationMetrics',
    'SystemIsolationHealth',
    'IsolationMetricsCollector',
    'get_isolation_metrics_collector',
    'start_request_tracking',
    'complete_request_tracking', 
    'record_instance_creation_time',
    'record_violation'
]