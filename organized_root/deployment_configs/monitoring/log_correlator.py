"""
Log correlation across services for deployment monitoring.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

@dataclass
class CorrelatedEvent:
    """Correlated event across services."""
    correlation_id: str
    services: List[str]
    start_time: datetime
    end_time: datetime
    event_count: int
    event_type: str  # request, error, deployment, etc.
    messages: List[str] = field(default_factory=list)
    trace_ids: Set[str] = field(default_factory=set)
    
    @property
    def duration_ms(self) -> float:
        """Get event duration in milliseconds."""
        return (self.end_time - self.start_time).total_seconds() * 1000

@dataclass
class ServiceDependency:
    """Service dependency relationship."""
    source_service: str
    target_service: str
    call_count: int = 0
    error_count: int = 0
    average_latency_ms: float = 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate for dependency."""
        return self.error_count / self.call_count if self.call_count > 0 else 0.0

class LogCorrelator:
    """Correlates logs across multiple services."""
    
    def __init__(self):
        self.correlated_events: Dict[str, CorrelatedEvent] = {}
        self.service_dependencies: Dict[Tuple[str, str], ServiceDependency] = {}
        self.trace_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    def correlate_logs(self, 
                       service_logs: Dict[str, List[Dict[str, Any]]]) -> List[CorrelatedEvent]:
        """
        Correlate logs across multiple services.
        
        Args:
            service_logs: Dictionary mapping service names to their logs
            
        Returns:
            List of correlated events
        """
        # Clear previous correlations
        self.correlated_events.clear()
        self.trace_map.clear()
        
        # Build trace map
        for service, logs in service_logs.items():
            for log in logs:
                trace_id = self._extract_trace_id(log)
                if trace_id:
                    self.trace_map[trace_id].append({
                        "service": service,
                        "log": log
                    })
        
        # Create correlated events from traces
        for trace_id, trace_logs in self.trace_map.items():
            if len(trace_logs) > 1:  # Only correlate if multiple services involved
                event = self._create_correlated_event(trace_id, trace_logs)
                if event:
                    self.correlated_events[trace_id] = event
        
        # Detect cascading failures
        cascading_failures = self._detect_cascading_failures(service_logs)
        for failure in cascading_failures:
            self.correlated_events[failure.correlation_id] = failure
        
        return list(self.correlated_events.values())
    
    def _extract_trace_id(self, log: Dict[str, Any]) -> Optional[str]:
        """Extract trace ID from log entry."""
        # Direct trace field
        if "trace" in log:
            return log["trace"]
        
        # From message patterns
        message = log.get("message", "") or log.get("textPayload", "")
        
        # Common trace patterns
        patterns = [
            r"trace[_-]?id[:\s]+([a-f0-9\-]+)",
            r"X-Trace-Id[:\s]+([a-f0-9\-]+)",
            r"correlation[_-]?id[:\s]+([a-f0-9\-]+)",
            r"request[_-]?id[:\s]+([a-f0-9\-]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _create_correlated_event(self, 
                                trace_id: str,
                                trace_logs: List[Dict[str, Any]]) -> Optional[CorrelatedEvent]:
        """Create a correlated event from trace logs."""
        if not trace_logs:
            return None
        
        # Extract timestamps
        timestamps = []
        services = set()
        messages = []
        
        for entry in trace_logs:
            service = entry["service"]
            log = entry["log"]
            
            services.add(service)
            
            # Parse timestamp
            timestamp_str = log.get("timestamp", "")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamps.append(timestamp)
                except:
                    pass
            
            # Collect messages
            message = log.get("message", "") or log.get("textPayload", "")
            if message:
                messages.append(f"[{service}] {message[:100]}")
        
        if not timestamps:
            return None
        
        # Determine event type
        event_type = self._determine_event_type(messages)
        
        return CorrelatedEvent(
            correlation_id=trace_id,
            services=list(services),
            start_time=min(timestamps),
            end_time=max(timestamps),
            event_count=len(trace_logs),
            event_type=event_type,
            messages=messages[:10],  # Limit message count
            trace_ids={trace_id}
        )
    
    def _determine_event_type(self, messages: List[str]) -> str:
        """Determine the type of correlated event."""
        combined = " ".join(messages).lower()
        
        if "error" in combined or "failed" in combined:
            return "error"
        elif "deployment" in combined or "deploy" in combined:
            return "deployment"
        elif "health" in combined:
            return "health_check"
        elif "request" in combined or "api" in combined:
            return "request"
        elif "timeout" in combined:
            return "timeout"
        else:
            return "unknown"
    
    def _detect_cascading_failures(self, 
                                  service_logs: Dict[str, List[Dict[str, Any]]]) -> List[CorrelatedEvent]:
        """Detect cascading failures across services."""
        cascading_failures = []
        
        # Group errors by time window (30 seconds)
        time_window = timedelta(seconds=30)
        error_windows = defaultdict(lambda: defaultdict(list))
        
        for service, logs in service_logs.items():
            for log in logs:
                severity = log.get("severity", "")
                if severity in ["ERROR", "CRITICAL", "EMERGENCY"]:
                    timestamp_str = log.get("timestamp", "")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                            window_key = timestamp.replace(second=0, microsecond=0)
                            error_windows[window_key][service].append(log)
                        except:
                            pass
        
        # Identify cascading failures (errors in 3+ services within same window)
        for window_time, service_errors in error_windows.items():
            if len(service_errors) >= 3:
                # Create correlated event for cascading failure
                all_logs = []
                services = []
                messages = []
                
                for service, errors in service_errors.items():
                    services.append(service)
                    for error in errors[:2]:  # Limit logs per service
                        message = error.get("message", "") or error.get("textPayload", "")
                        messages.append(f"[{service}] {message[:100]}")
                        all_logs.append(error)
                
                if all_logs:
                    cascading_failures.append(CorrelatedEvent(
                        correlation_id=f"cascade_{window_time.isoformat()}",
                        services=services,
                        start_time=window_time,
                        end_time=window_time + time_window,
                        event_count=sum(len(errors) for errors in service_errors.values()),
                        event_type="cascading_failure",
                        messages=messages
                    ))
        
        return cascading_failures
    
    def analyze_service_dependencies(self, 
                                    correlated_events: List[CorrelatedEvent]) -> Dict[Tuple[str, str], ServiceDependency]:
        """
        Analyze service dependencies from correlated events.
        
        Args:
            correlated_events: List of correlated events
            
        Returns:
            Dictionary of service dependencies
        """
        self.service_dependencies.clear()
        
        for event in correlated_events:
            if len(event.services) >= 2:
                # Assume first service calls second (simplified)
                for i in range(len(event.services) - 1):
                    source = event.services[i]
                    target = event.services[i + 1]
                    key = (source, target)
                    
                    if key not in self.service_dependencies:
                        self.service_dependencies[key] = ServiceDependency(
                            source_service=source,
                            target_service=target
                        )
                    
                    dep = self.service_dependencies[key]
                    dep.call_count += 1
                    
                    if event.event_type == "error":
                        dep.error_count += 1
                    
                    # Update latency (simplified)
                    if dep.average_latency_ms == 0:
                        dep.average_latency_ms = event.duration_ms
                    else:
                        dep.average_latency_ms = (dep.average_latency_ms + event.duration_ms) / 2
        
        return self.service_dependencies
    
    def detect_anomalies(self, 
                        correlated_events: List[CorrelatedEvent]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in correlated events.
        
        Args:
            correlated_events: List of correlated events
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Check for unusual event durations
        durations = [e.duration_ms for e in correlated_events if e.duration_ms > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            std_dev = (sum((d - avg_duration) ** 2 for d in durations) / len(durations)) ** 0.5
            
            for event in correlated_events:
                if event.duration_ms > avg_duration + (2 * std_dev):
                    anomalies.append({
                        "type": "high_latency",
                        "correlation_id": event.correlation_id,
                        "services": event.services,
                        "duration_ms": event.duration_ms,
                        "threshold_ms": avg_duration + (2 * std_dev)
                    })
        
        # Check for cascading failures
        cascading = [e for e in correlated_events if e.event_type == "cascading_failure"]
        for event in cascading:
            anomalies.append({
                "type": "cascading_failure",
                "correlation_id": event.correlation_id,
                "services": event.services,
                "event_count": event.event_count,
                "time": event.start_time.isoformat()
            })
        
        # Check for high error rates in dependencies
        for dep in self.service_dependencies.values():
            if dep.error_rate > 0.1:  # 10% error rate threshold
                anomalies.append({
                    "type": "high_error_rate",
                    "source": dep.source_service,
                    "target": dep.target_service,
                    "error_rate": dep.error_rate,
                    "call_count": dep.call_count
                })
        
        return anomalies
    
    def generate_correlation_report(self, 
                                   correlated_events: List[CorrelatedEvent]) -> str:
        """
        Generate a correlation report.
        
        Args:
            correlated_events: List of correlated events
            
        Returns:
            Formatted report string
        """
        lines = [
            "LOG CORRELATION REPORT",
            "=" * 60,
            f"Total Correlated Events: {len(correlated_events)}",
            ""
        ]
        
        # Group by event type
        by_type = defaultdict(list)
        for event in correlated_events:
            by_type[event.event_type].append(event)
        
        lines.append("Events by Type:")
        for event_type, events in sorted(by_type.items()):
            lines.append(f"  {event_type}: {len(events)}")
        
        # Cascading failures
        cascading = [e for e in correlated_events if e.event_type == "cascading_failure"]
        if cascading:
            lines.extend(["", "CASCADING FAILURES:"])
            for event in cascading[:5]:  # Limit to 5
                lines.append(f"  Time: {event.start_time.isoformat()}")
                lines.append(f"  Services: {', '.join(event.services)}")
                lines.append(f"  Event Count: {event.event_count}")
                lines.append("")
        
        # Service dependencies
        if self.service_dependencies:
            lines.extend(["SERVICE DEPENDENCIES:"])
            for dep in sorted(self.service_dependencies.values(), 
                            key=lambda x: x.error_rate, reverse=True)[:10]:
                lines.append(f"  {dep.source_service} → {dep.target_service}")
                lines.append(f"    Calls: {dep.call_count}, Errors: {dep.error_count}")
                lines.append(f"    Error Rate: {dep.error_rate:.2%}")
                lines.append(f"    Avg Latency: {dep.average_latency_ms:.2f}ms")
        
        # Anomalies
        anomalies = self.detect_anomalies(correlated_events)
        if anomalies:
            lines.extend(["", "DETECTED ANOMALIES:"])
            for anomaly in anomalies[:10]:  # Limit to 10
                lines.append(f"  Type: {anomaly['type']}")
                for key, value in anomaly.items():
                    if key != "type":
                        lines.append(f"    {key}: {value}")
                lines.append("")
        
        return "\n".join(lines)
    
    def visualize_service_graph(self) -> str:
        """
        Generate ASCII visualization of service dependencies.
        
        Returns:
            ASCII art representation of service graph
        """
        if not self.service_dependencies:
            return "No service dependencies detected"
        
        lines = ["SERVICE DEPENDENCY GRAPH", "=" * 40]
        
        # Group by source service
        by_source = defaultdict(list)
        for dep in self.service_dependencies.values():
            by_source[dep.source_service].append(dep)
        
        for source, deps in sorted(by_source.items()):
            lines.append(f"\n{source}")
            for dep in deps:
                error_indicator = " ⚠" if dep.error_rate > 0.1 else ""
                lines.append(f"  └─→ {dep.target_service} "
                           f"(calls: {dep.call_count}, "
                           f"errors: {dep.error_rate:.1%}){error_indicator}")
        
        return "\n".join(lines)