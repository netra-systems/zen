"""Failure Detector Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic failure detection functionality for tests
- Value Impact: Ensures failure detection tests can execute without import errors
- Strategic Impact: Enables failure detection functionality validation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class FailureType(Enum):
    """Types of failures that can be detected."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    UNKNOWN = "unknown"


@dataclass
class FailureEvent:
    """Represents a failure event."""
    service_name: str
    failure_type: FailureType
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical
    error_code: Optional[str] = None


@dataclass
class FailurePattern:
    """Pattern of failures for analysis."""
    service_name: str
    failure_type: FailureType
    count: int = 0
    first_occurrence: Optional[datetime] = None
    last_occurrence: Optional[datetime] = None
    frequency_per_minute: float = 0.0


class FailureDetector:
    """Detects and analyzes failure patterns in services."""
    
    def __init__(self):
        """Initialize failure detector."""
        self._failures: List[FailureEvent] = []
        self._failure_listeners: List[Callable[[FailureEvent], None]] = []
        self._pattern_listeners: List[Callable[[FailurePattern], None]] = []
        self._lock = asyncio.Lock()
        self._analysis_task: Optional[asyncio.Task] = None
        self._running = False
        self._analysis_interval = 60  # seconds
        self._max_failure_history = 1000  # Keep last 1000 failures
    
    async def start(self) -> None:
        """Start the failure detector."""
        self._running = True
        self._analysis_task = asyncio.create_task(self._analysis_loop())
    
    async def stop(self) -> None:
        """Stop the failure detector."""
        self._running = False
        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass
    
    async def record_failure(
        self,
        service_name: str,
        failure_type: FailureType,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
        error_code: Optional[str] = None
    ) -> None:
        """Record a failure event."""
        failure_event = FailureEvent(
            service_name=service_name,
            failure_type=failure_type,
            message=message,
            details=details or {},
            severity=severity,
            error_code=error_code
        )
        
        async with self._lock:
            self._failures.append(failure_event)
            
            # Trim old failures to prevent memory growth
            if len(self._failures) > self._max_failure_history:
                self._failures = self._failures[-self._max_failure_history:]
        
        # Notify listeners
        await self._notify_failure_listeners(failure_event)
    
    async def get_failure_count(
        self,
        service_name: Optional[str] = None,
        failure_type: Optional[FailureType] = None,
        since: Optional[datetime] = None
    ) -> int:
        """Get count of failures matching criteria."""
        async with self._lock:
            failures = self._failures
        
        if service_name:
            failures = [f for f in failures if f.service_name == service_name]
        
        if failure_type:
            failures = [f for f in failures if f.failure_type == failure_type]
        
        if since:
            failures = [f for f in failures if f.timestamp >= since]
        
        return len(failures)
    
    async def get_recent_failures(
        self,
        service_name: Optional[str] = None,
        minutes: int = 60,
        limit: int = 100
    ) -> List[FailureEvent]:
        """Get recent failures for a service."""
        since = datetime.now() - timedelta(minutes=minutes)
        
        async with self._lock:
            failures = [
                f for f in self._failures
                if f.timestamp >= since and (service_name is None or f.service_name == service_name)
            ]
        
        # Return most recent failures first
        failures.sort(key=lambda x: x.timestamp, reverse=True)
        return failures[:limit]
    
    async def detect_failure_patterns(self, service_name: Optional[str] = None) -> List[FailurePattern]:
        """Detect failure patterns in the data."""
        # Analyze failures from the last hour
        since = datetime.now() - timedelta(hours=1)
        
        async with self._lock:
            failures = [
                f for f in self._failures
                if f.timestamp >= since and (service_name is None or f.service_name == service_name)
            ]
        
        # Group failures by service and type
        pattern_map: Dict[str, FailurePattern] = {}
        
        for failure in failures:
            key = f"{failure.service_name}:{failure.failure_type.value}"
            
            if key not in pattern_map:
                pattern_map[key] = FailurePattern(
                    service_name=failure.service_name,
                    failure_type=failure.failure_type,
                    first_occurrence=failure.timestamp,
                    last_occurrence=failure.timestamp,
                    count=1
                )
            else:
                pattern = pattern_map[key]
                pattern.count += 1
                pattern.last_occurrence = failure.timestamp
                if failure.timestamp < pattern.first_occurrence:
                    pattern.first_occurrence = failure.timestamp
        
        # Calculate frequency
        for pattern in pattern_map.values():
            if pattern.first_occurrence and pattern.last_occurrence:
                duration_minutes = (pattern.last_occurrence - pattern.first_occurrence).total_seconds() / 60
                if duration_minutes > 0:
                    pattern.frequency_per_minute = pattern.count / duration_minutes
                else:
                    pattern.frequency_per_minute = pattern.count  # All failures in same minute
        
        return list(pattern_map.values())
    
    async def is_service_failing(
        self,
        service_name: str,
        failure_threshold: int = 5,
        time_window_minutes: int = 10
    ) -> bool:
        """Check if a service is currently experiencing failures."""
        since = datetime.now() - timedelta(minutes=time_window_minutes)
        failure_count = await self.get_failure_count(service_name=service_name, since=since)
        return failure_count >= failure_threshold
    
    async def get_service_health_score(self, service_name: str, hours: int = 1) -> float:
        """Calculate a health score for a service (0.0 = unhealthy, 1.0 = healthy)."""
        since = datetime.now() - timedelta(hours=hours)
        failure_count = await self.get_failure_count(service_name=service_name, since=since)
        
        # Simple scoring: reduce score based on failure count
        # This is a basic implementation - in reality, you'd consider severity, frequency, etc.
        max_expected_failures = 10  # Configurable threshold
        
        if failure_count == 0:
            return 1.0
        elif failure_count >= max_expected_failures:
            return 0.0
        else:
            return 1.0 - (failure_count / max_expected_failures)
    
    async def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of all failures."""
        async with self._lock:
            total_failures = len(self._failures)
            
            if total_failures == 0:
                return {
                    "total_failures": 0,
                    "services_affected": 0,
                    "failure_types": {},
                    "severity_breakdown": {},
                    "recent_failures_per_minute": 0.0
                }
            
            # Calculate summary statistics
            services = set(f.service_name for f in self._failures)
            failure_types = {}
            severity_breakdown = {}
            
            for failure in self._failures:
                failure_types[failure.failure_type.value] = failure_types.get(failure.failure_type.value, 0) + 1
                severity_breakdown[failure.severity] = severity_breakdown.get(failure.severity, 0) + 1
            
            # Calculate recent failure rate
            recent_since = datetime.now() - timedelta(minutes=10)
            recent_failures = [f for f in self._failures if f.timestamp >= recent_since]
            recent_failures_per_minute = len(recent_failures) / 10.0
            
            return {
                "total_failures": total_failures,
                "services_affected": len(services),
                "failure_types": failure_types,
                "severity_breakdown": severity_breakdown,
                "recent_failures_per_minute": recent_failures_per_minute
            }
    
    def add_failure_listener(self, listener: Callable[[FailureEvent], None]) -> None:
        """Add a listener for failure events."""
        self._failure_listeners.append(listener)
    
    def add_pattern_listener(self, listener: Callable[[FailurePattern], None]) -> None:
        """Add a listener for failure patterns."""
        self._pattern_listeners.append(listener)
    
    async def clear_failures(self) -> None:
        """Clear all recorded failures."""
        async with self._lock:
            self._failures.clear()
    
    async def _analysis_loop(self) -> None:
        """Background analysis loop for detecting patterns."""
        while self._running:
            try:
                # Detect patterns and notify listeners
                patterns = await self.detect_failure_patterns()
                for pattern in patterns:
                    # Notify if pattern shows concerning trends
                    if pattern.frequency_per_minute > 1.0:  # More than 1 failure per minute
                        await self._notify_pattern_listeners(pattern)
                
                await asyncio.sleep(self._analysis_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue analysis
                await asyncio.sleep(5)
    
    async def _notify_failure_listeners(self, failure_event: FailureEvent) -> None:
        """Notify listeners about failure events."""
        for listener in self._failure_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(failure_event)
                else:
                    listener(failure_event)
            except Exception as e:
                # Log error but continue with other listeners
                pass
    
    async def _notify_pattern_listeners(self, pattern: FailurePattern) -> None:
        """Notify listeners about failure patterns."""
        for listener in self._pattern_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(pattern)
                else:
                    listener(pattern)
            except Exception as e:
                # Log error but continue with other listeners
                pass


# Helper functions for common failure detection
async def detect_timeout_failure(service_name: str, timeout_seconds: float) -> Optional[FailureEvent]:
    """Helper to detect timeout failures."""
    # This would be used in actual service calls
    return None


async def detect_http_failure(service_name: str, status_code: int, response_time: float) -> Optional[FailureEvent]:
    """Helper to detect HTTP failures."""
    if status_code >= 500:
        return FailureEvent(
            service_name=service_name,
            failure_type=FailureType.HTTP_ERROR,
            message=f"HTTP {status_code} error",
            details={"status_code": status_code, "response_time": response_time},
            severity="high" if status_code >= 500 else "medium"
        )
    return None


# Global failure detector instance
default_failure_detector = FailureDetector()