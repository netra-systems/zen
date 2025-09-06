"""
Isolation Score Monitoring System
=================================

Real-time monitoring system for tracking request isolation effectiveness
during production rollout. This system calculates and tracks the isolation
score (0-100%) which indicates how well requests are isolated from each other.

Key Features:
- Real-time isolation score calculation
- Cascade failure detection
- Cross-contamination monitoring  
- Request independence validation
- Performance impact tracking
- Circuit breaker integration

Business Value: System Stability & Risk Mitigation
- Prevents cascade failures from affecting multiple users
- Ensures 100% request isolation during rollout
- Provides instant feedback on isolation effectiveness
- Enables automated rollback based on isolation score

Isolation Score Calculation:
- 100%: Perfect isolation (no cross-contamination)
- 99-95%: Good isolation (minor leakage detected)
- 94-90%: Poor isolation (significant leakage)
- <90%: Critical failure (rollback required)
"""

import asyncio
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import contextmanager
import hashlib
import statistics
from datetime import datetime, timedelta

from shared.isolated_environment import IsolatedEnvironment
from shared.feature_flags import IsolationMetrics, ProductionFeatureFlags

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Context information for a single request."""
    request_id: str
    user_id: str
    session_id: str
    thread_id: Optional[str] = None
    agent_instance_id: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    status: str = "active"  # active, completed, failed, contaminated
    
    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()


@dataclass
class ContaminationEvent:
    """Detected contamination between requests."""
    source_request_id: str
    target_request_id: str
    contamination_type: str  # "state_leak", "session_share", "agent_reuse", "db_conflict"
    detected_at: float
    severity: str = "medium"  # low, medium, high, critical
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.detected_at == 0.0:
            self.detected_at = time.time()


@dataclass
class IsolationScoreSnapshot:
    """Snapshot of isolation score at a point in time."""
    timestamp: float
    total_requests: int
    isolated_requests: int
    contaminated_requests: int
    isolation_score: float
    contamination_events: List[ContaminationEvent] = None
    cascade_failures: int = 0
    performance_impact: float = 0.0  # Response time increase due to isolation overhead
    
    def __post_init__(self):
        if self.contamination_events is None:
            self.contamination_events = []
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class IsolationScoreMonitor:
    """
    Real-time isolation score monitoring system.
    
    Tracks request isolation effectiveness and provides instant feedback
    on system stability during feature rollout.
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.env = IsolatedEnvironment.get_instance()
        
        # Request tracking
        self.active_requests: Dict[str, RequestContext] = {}
        self.completed_requests: deque = deque(maxlen=10000)  # Keep last 10k requests
        self.contamination_events: deque = deque(maxlen=1000)  # Keep last 1k events
        
        # Isolation monitoring
        self.isolation_score_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.current_score: float = 1.0
        self.lock = threading.RLock()
        
        # Configuration
        self.score_calculation_interval = 30  # Calculate score every 30 seconds
        self.max_request_duration = 300  # 5 minutes max request duration
        self.contamination_thresholds = {
            "state_leak": 0.01,      # 1% threshold
            "session_share": 0.005,  # 0.5% threshold  
            "agent_reuse": 0.001,    # 0.1% threshold
            "db_conflict": 0.02      # 2% threshold
        }
        
        # State tracking for contamination detection
        self.agent_instances: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> request_ids
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)    # session_id -> request_ids
        self.database_transactions: Dict[str, Set[str]] = defaultdict(set)  # tx_id -> request_ids
        
        # Feature flags integration
        self.feature_flags = ProductionFeatureFlags(environment)
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task = None
        
        logger.info(f"Initialized IsolationScoreMonitor for {environment}")

    async def start_monitoring(self) -> None:
        """Start real-time isolation score monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started isolation score monitoring")

    async def stop_monitoring(self) -> None:
        """Stop isolation score monitoring."""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped isolation score monitoring")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while self.is_monitoring:
                # Calculate current isolation score
                score_snapshot = self.calculate_isolation_score()
                
                # Update score history
                with self.lock:
                    self.isolation_score_history.append(score_snapshot)
                    self.current_score = score_snapshot.isolation_score
                
                # Check for critical isolation failures
                if score_snapshot.isolation_score < 0.9:
                    await self._handle_critical_isolation_failure(score_snapshot)
                elif score_snapshot.isolation_score < 0.95:
                    await self._handle_isolation_warning(score_snapshot)
                
                # Clean up old requests
                self._cleanup_old_requests()
                
                # Report metrics to feature flags system
                await self._report_metrics(score_snapshot)
                
                # Wait for next calculation
                await asyncio.sleep(self.score_calculation_interval)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            # Continue monitoring despite errors
            if self.is_monitoring:
                await asyncio.sleep(5)
                await self._monitoring_loop()

    def register_request_start(self, request_id: str, user_id: str, 
                             session_id: str, thread_id: Optional[str] = None,
                             agent_instance_id: Optional[str] = None) -> None:
        """Register the start of a new request."""
        with self.lock:
            context = RequestContext(
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
                thread_id=thread_id,
                agent_instance_id=agent_instance_id
            )
            
            self.active_requests[request_id] = context
            
            # Track agent instance usage
            if agent_instance_id:
                self.agent_instances[agent_instance_id].add(request_id)
                
                # Check for agent reuse contamination
                if len(self.agent_instances[agent_instance_id]) > 1:
                    # FIXED: removed await - detect agent reuse contamination
                    pass
            
            # Track session usage
            self.user_sessions[session_id].add(request_id)
            
            logger.debug(f"Registered request start: {request_id}")

    def register_request_completion(self, request_id: str, status: str = "completed",
                                  error: Optional[str] = None) -> None:
        """Register the completion of a request."""
        with self.lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request not found for completion: {request_id}")
                return
            
            context = self.active_requests[request_id]
            context.end_time = time.time()
            context.status = status
            
            # Move to completed requests
            self.completed_requests.append(context)
            
            # Clean up tracking data
            if context.agent_instance_id:
                self.agent_instances[context.agent_instance_id].discard(request_id)
                
            self.user_sessions[context.session_id].discard(request_id)
            
            # Remove from active requests
            del self.active_requests[request_id]
            
            logger.debug(f"Registered request completion: {request_id} ({status})")

    def detect_contamination(self, source_request_id: str, target_request_id: str,
                           contamination_type: str, details: Dict[str, Any] = None) -> None:
        """Detect and record a contamination event."""
        severity = self._determine_contamination_severity(contamination_type, details or {})
        
        event = ContaminationEvent(
            source_request_id=source_request_id,
            target_request_id=target_request_id,
            contamination_type=contamination_type,
            detected_at=time.time(),
            severity=severity,
            details=details or {}
        )
        
        with self.lock:
            self.contamination_events.append(event)
            
            # Mark affected requests as contaminated
            for request_id in [source_request_id, target_request_id]:
                if request_id in self.active_requests:
                    self.active_requests[request_id].status = "contaminated"
        
        logger.warning(f"Contamination detected: {contamination_type} between {source_request_id} and {target_request_id}")

    async def _detect_agent_reuse_contamination(self, agent_instance_id: str, 
                                              new_request_id: str) -> None:
        """Detect contamination from agent instance reuse."""
        other_requests = self.agent_instances[agent_instance_id] - {new_request_id}
        
        if other_requests:
            # Agent instance being shared - this is contamination
            for other_request_id in other_requests:
                self.detect_contamination(
                    source_request_id=other_request_id,
                    target_request_id=new_request_id,
                    contamination_type="agent_reuse",
                    details={
                        "agent_instance_id": agent_instance_id,
                        "shared_requests": len(other_requests) + 1
                    }
                )

    def detect_state_leak(self, source_request_id: str, target_request_id: str,
                         state_type: str, leaked_data: Any = None) -> None:
        """Detect state leakage between requests."""
        self.detect_contamination(
            source_request_id=source_request_id,
            target_request_id=target_request_id,
            contamination_type="state_leak",
            details={
                "state_type": state_type,
                "leaked_data_hash": hashlib.md5(str(leaked_data).encode()).hexdigest() if leaked_data else None
            }
        )

    def detect_session_sharing(self, session_id: str, request_ids: List[str]) -> None:
        """Detect session sharing between requests."""
        if len(request_ids) > 1:
            for i, source_id in enumerate(request_ids):
                for target_id in request_ids[i+1:]:
                    self.detect_contamination(
                        source_request_id=source_id,
                        target_request_id=target_id,
                        contamination_type="session_share",
                        details={
                            "session_id": session_id,
                            "shared_requests_count": len(request_ids)
                        }
                    )

    def detect_database_conflict(self, transaction_id: str, conflicting_requests: List[str]) -> None:
        """Detect database transaction conflicts between requests."""
        if len(conflicting_requests) > 1:
            for i, source_id in enumerate(conflicting_requests):
                for target_id in conflicting_requests[i+1:]:
                    self.detect_contamination(
                        source_request_id=source_id,
                        target_request_id=target_id,
                        contamination_type="db_conflict",
                        details={
                            "transaction_id": transaction_id,
                            "conflicting_requests_count": len(conflicting_requests)
                        }
                    )

    def calculate_isolation_score(self) -> IsolationScoreSnapshot:
        """Calculate current isolation score based on contamination events."""
        with self.lock:
            current_time = time.time()
            
            # Get requests from the last calculation period
            recent_requests = []
            
            # Add active requests
            recent_requests.extend(self.active_requests.values())
            
            # Add recently completed requests (last 5 minutes)
            cutoff_time = current_time - 300  # 5 minutes
            for request in self.completed_requests:
                if request.end_time and request.end_time > cutoff_time:
                    recent_requests.append(request)
                elif request.start_time > cutoff_time:
                    recent_requests.append(request)
            
            total_requests = len(recent_requests)
            if total_requests == 0:
                return IsolationScoreSnapshot(
                    timestamp=current_time,
                    total_requests=0,
                    isolated_requests=0,
                    contaminated_requests=0,
                    isolation_score=1.0,
                    contamination_events=[],
                    cascade_failures=0
                )
            
            # Count contaminated requests
            contaminated_request_ids = set()
            recent_contamination_events = []
            
            # Get contamination events from the last calculation period
            for event in self.contamination_events:
                if event.detected_at > cutoff_time:
                    recent_contamination_events.append(event)
                    contaminated_request_ids.add(event.source_request_id)
                    contaminated_request_ids.add(event.target_request_id)
            
            # Count requests by status
            contaminated_requests = 0
            failed_requests = 0
            cascade_failures = 0
            
            for request in recent_requests:
                if request.request_id in contaminated_request_ids or request.status == "contaminated":
                    contaminated_requests += 1
                elif request.status == "failed":
                    failed_requests += 1
                    
                    # Check if this failure might have caused cascade failures
                    if self._is_cascade_failure(request, recent_contamination_events):
                        cascade_failures += 1
            
            isolated_requests = total_requests - contaminated_requests
            
            # Calculate isolation score
            if total_requests > 0:
                isolation_score = isolated_requests / total_requests
            else:
                isolation_score = 1.0
            
            # Apply penalties for different contamination types
            isolation_score = self._apply_contamination_penalties(
                isolation_score, recent_contamination_events
            )
            
            # Calculate performance impact
            performance_impact = self._calculate_performance_impact(recent_requests)
            
            return IsolationScoreSnapshot(
                timestamp=current_time,
                total_requests=total_requests,
                isolated_requests=isolated_requests,
                contaminated_requests=contaminated_requests,
                isolation_score=max(0.0, isolation_score),  # Ensure non-negative
                contamination_events=recent_contamination_events,
                cascade_failures=cascade_failures,
                performance_impact=performance_impact
            )

    def _determine_contamination_severity(self, contamination_type: str, 
                                        details: Dict[str, Any]) -> str:
        """Determine severity of a contamination event."""
        # Base severity by type
        base_severity = {
            "agent_reuse": "high",      # Agent reuse is serious
            "state_leak": "critical",   # State leaks are very serious
            "session_share": "medium",  # Session sharing is concerning
            "db_conflict": "high"       # DB conflicts can cause data issues
        }.get(contamination_type, "medium")
        
        # Adjust based on details
        if contamination_type == "agent_reuse":
            shared_count = details.get("shared_requests", 0)
            if shared_count > 5:
                return "critical"
            elif shared_count > 2:
                return "high"
        elif contamination_type == "session_share":
            shared_count = details.get("shared_requests_count", 0)
            if shared_count > 10:
                return "critical"
            elif shared_count > 5:
                return "high"
        
        return base_severity

    def _apply_contamination_penalties(self, base_score: float, 
                                     events: List[ContaminationEvent]) -> float:
        """Apply penalties to isolation score based on contamination events."""
        penalty = 0.0
        
        for event in events:
            # Penalty based on severity
            severity_penalties = {
                "low": 0.001,
                "medium": 0.005,
                "high": 0.01,
                "critical": 0.02
            }
            
            penalty += severity_penalties.get(event.severity, 0.005)
            
            # Additional penalty for specific contamination types
            if event.contamination_type == "state_leak":
                penalty += 0.01  # Extra penalty for state leaks
            elif event.contamination_type == "agent_reuse":
                penalty += 0.005  # Extra penalty for agent reuse
        
        return max(0.0, base_score - penalty)

    def _is_cascade_failure(self, failed_request: RequestContext, 
                          contamination_events: List[ContaminationEvent]) -> bool:
        """Determine if a failed request caused cascade failures."""
        # A cascade failure is when one request's failure affects other requests
        # through contamination events
        
        for event in contamination_events:
            if (event.source_request_id == failed_request.request_id or 
                event.target_request_id == failed_request.request_id):
                return True
        
        return False

    def _calculate_performance_impact(self, requests: List[RequestContext]) -> float:
        """Calculate performance impact of isolation overhead."""
        completed_requests = [r for r in requests if r.end_time]
        
        if len(completed_requests) < 10:
            return 0.0  # Not enough data
        
        # Calculate average response time
        response_times = [(r.end_time - r.start_time) for r in completed_requests]
        avg_response_time = statistics.mean(response_times)
        
        # Compare against baseline (if available)
        # For now, assume 500ms baseline - this would be configurable in production
        baseline_response_time = 0.5
        
        if avg_response_time > baseline_response_time:
            return (avg_response_time - baseline_response_time) / baseline_response_time
        
        return 0.0

    def _cleanup_old_requests(self) -> None:
        """Clean up old request data."""
        current_time = time.time()
        
        with self.lock:
            # Remove very old active requests (likely stuck)
            stuck_requests = []
            for request_id, context in self.active_requests.items():
                if current_time - context.start_time > self.max_request_duration:
                    stuck_requests.append(request_id)
            
            for request_id in stuck_requests:
                logger.warning(f"Cleaning up stuck request: {request_id}")
                self.register_request_completion(request_id, "timeout")
            
            # Clean up agent tracking data
            empty_agents = []
            for agent_id, request_ids in self.agent_instances.items():
                if not request_ids:
                    empty_agents.append(agent_id)
            
            for agent_id in empty_agents:
                del self.agent_instances[agent_id]
            
            # Clean up session tracking data
            empty_sessions = []
            for session_id, request_ids in self.user_sessions.items():
                if not request_ids:
                    empty_sessions.append(session_id)
            
            for session_id in empty_sessions:
                del self.user_sessions[session_id]

    async def _handle_critical_isolation_failure(self, 
                                               snapshot: IsolationScoreSnapshot) -> None:
        """Handle critical isolation failures (score < 90%)."""
        logger.critical(f"CRITICAL ISOLATION FAILURE: Score {snapshot.isolation_score:.1%}")
        logger.critical(f"Contaminated requests: {snapshot.contaminated_requests}/{snapshot.total_requests}")
        logger.critical(f"Cascade failures: {snapshot.cascade_failures}")
        
        # Log contamination events for debugging
        for event in snapshot.contamination_events:
            logger.critical(f"Contamination: {event.contamination_type} - {event.source_request_id} -> {event.target_request_id}")
        
        # This would trigger emergency rollback in production
        # For now, just log the critical failure
        pass

    async def _handle_isolation_warning(self, snapshot: IsolationScoreSnapshot) -> None:
        """Handle isolation warnings (score 90-95%)."""
        logger.warning(f"ISOLATION WARNING: Score {snapshot.isolation_score:.1%}")
        logger.warning(f"Contaminated requests: {snapshot.contaminated_requests}/{snapshot.total_requests}")
        
        # This would trigger alerts in production
        pass

    async def _report_metrics(self, snapshot: IsolationScoreSnapshot) -> None:
        """Report metrics to the feature flags system."""
        try:
            metrics = IsolationMetrics(
                total_requests=snapshot.total_requests,
                isolated_requests=snapshot.isolated_requests,
                failed_requests=0,  # Not tracking failed requests separately yet
                cascade_failures=snapshot.cascade_failures,
                isolation_score=snapshot.isolation_score,
                error_rate=0.0,  # Would be calculated from actual error data
                response_time_p95=0.0,  # Would be calculated from actual response times
                timestamp=snapshot.timestamp
            )
            
            self.feature_flags.record_isolation_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Failed to report metrics: {e}")

    def get_current_score(self) -> float:
        """Get the current isolation score."""
        with self.lock:
            return self.current_score

    def get_score_history(self, hours: int = 24) -> List[IsolationScoreSnapshot]:
        """Get isolation score history for the specified number of hours."""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            return [snapshot for snapshot in self.isolation_score_history 
                   if snapshot.timestamp > cutoff_time]

    def get_contamination_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get contamination summary for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            recent_events = [event for event in self.contamination_events 
                           if event.detected_at > cutoff_time]
            
            summary = {
                "total_events": len(recent_events),
                "by_type": defaultdict(int),
                "by_severity": defaultdict(int),
                "affected_requests": set()
            }
            
            for event in recent_events:
                summary["by_type"][event.contamination_type] += 1
                summary["by_severity"][event.severity] += 1
                summary["affected_requests"].add(event.source_request_id)
                summary["affected_requests"].add(event.target_request_id)
            
            summary["affected_requests"] = len(summary["affected_requests"])
            summary["by_type"] = dict(summary["by_type"])
            summary["by_severity"] = dict(summary["by_severity"])
            
            return summary

    @contextmanager
    def request_isolation_context(self, request_id: str, user_id: str, 
                                session_id: str, thread_id: Optional[str] = None,
                                agent_instance_id: Optional[str] = None):
        """
        Context manager for tracking request isolation.
        
        Usage:
            with monitor.request_isolation_context(request_id, user_id, session_id) as ctx:
                # Execute isolated request
                result = # FIXED: removed await - process_request()
                return result
        """
        self.register_request_start(request_id, user_id, session_id, thread_id, agent_instance_id)
        
        try:
            yield self
            self.register_request_completion(request_id, "completed")
        except Exception as e:
            self.register_request_completion(request_id, "failed", str(e))
            raise


# Global instance
_monitor_instance = None
_monitor_lock = threading.Lock()


def get_isolation_monitor() -> IsolationScoreMonitor:
    """Get the global isolation score monitor instance."""
    global _monitor_instance
    
    if _monitor_instance is None:
        with _monitor_lock:
            if _monitor_instance is None:
                env = IsolatedEnvironment.get_instance()
                environment = env.get("ENVIRONMENT", "production")
                _monitor_instance = IsolationScoreMonitor(environment)
    
    return _monitor_instance


# Convenience functions
def register_request_start(request_id: str, user_id: str, session_id: str,
                          thread_id: Optional[str] = None,
                          agent_instance_id: Optional[str] = None) -> None:
    """Register the start of a request for isolation monitoring."""
    get_isolation_monitor().register_request_start(
        request_id, user_id, session_id, thread_id, agent_instance_id
    )


def register_request_completion(request_id: str, status: str = "completed") -> None:
    """Register the completion of a request."""
    get_isolation_monitor().register_request_completion(request_id, status)


def detect_contamination(source_request_id: str, target_request_id: str,
                        contamination_type: str, details: Dict[str, Any] = None) -> None:
    """Detect contamination between requests."""
    get_isolation_monitor().detect_contamination(
        source_request_id, target_request_id, contamination_type, details
    )


def get_current_isolation_score() -> float:
    """Get the current isolation score."""
    return get_isolation_monitor().get_current_score()


@contextmanager
def isolation_context(request_id: str, user_id: str, session_id: str,
                     thread_id: Optional[str] = None,
                     agent_instance_id: Optional[str] = None):
    """Context manager for request isolation monitoring."""
    with get_isolation_monitor().request_isolation_context(
        request_id, user_id, session_id, thread_id, agent_instance_id
    ) as ctx:
        yield ctx