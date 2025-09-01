"""Runtime Event Flow Monitoring for Chat System.

Business Value: Detects silent failures in real-time to prevent user abandonment.
Monitors critical event flow and alerts when events are missing or delayed.
"""

import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EventType(Enum):
    """Critical WebSocket event types."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    ERROR = "error"


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class ChatEventMonitor:
    """
    Monitor critical chat event flow in real-time.
    
    Features:
    - Tracks event flow per thread
    - Detects missing events (e.g., tool_executing without tool_completed)
    - Identifies stale threads (no events for extended period)
    - Monitors event delivery latency
    - Provides health status and alerts
    """
    
    def __init__(self):
        # Event tracking
        self.event_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.last_event_time: Dict[str, float] = {}
        self.thread_start_time: Dict[str, float] = {}
        self.active_tools: Dict[str, Set[str]] = defaultdict(set)  # thread_id -> set of executing tools
        
        # Event flow tracking
        self.expected_sequences: Dict[str, List[str]] = {}  # thread_id -> expected next events
        self.event_history: Dict[str, List[Dict]] = defaultdict(list)  # thread_id -> event history
        
        # Latency tracking
        self.event_latencies: List[float] = []
        self.max_latency_samples = 1000
        
        # Alert thresholds
        self.stale_thread_threshold = 30  # seconds without events
        self.tool_timeout_threshold = 60  # seconds for tool execution
        self.latency_warning_threshold = 1.0  # seconds
        self.latency_critical_threshold = 5.0  # seconds
        
        # Silent failure detection
        self.silent_failures: List[Dict] = []
        self.max_silent_failures = 100
        
        # Background monitoring
        self._monitor_task = None
        self._shutdown = False
        
    async def record_event(
        self, 
        event_type: str, 
        thread_id: str,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record an event occurrence and check for anomalies."""
        now = time.time()
        
        # Track event
        key = f"{thread_id}:{event_type}"
        self.event_counts[thread_id][event_type] += 1
        self.last_event_time[key] = now
        
        # Track thread lifecycle
        if event_type == EventType.AGENT_STARTED.value:
            self.thread_start_time[thread_id] = now
            self.expected_sequences[thread_id] = [
                EventType.AGENT_THINKING.value,
                EventType.TOOL_EXECUTING.value
            ]
        
        # Track tool execution
        if event_type == EventType.TOOL_EXECUTING.value and tool_name:
            self.active_tools[thread_id].add(tool_name)
            # Expect tool_completed next
            self.expected_sequences[thread_id] = [EventType.TOOL_COMPLETED.value]
            
        elif event_type == EventType.TOOL_COMPLETED.value and tool_name:
            if tool_name in self.active_tools[thread_id]:
                self.active_tools[thread_id].remove(tool_name)
            else:
                # Tool completed without executing - silent failure!
                await self._record_silent_failure(
                    thread_id,
                    f"tool_completed without tool_executing for {tool_name}",
                    {"tool_name": tool_name}
                )
        
        # Track event history
        self.event_history[thread_id].append({
            "event_type": event_type,
            "timestamp": now,
            "tool_name": tool_name,
            "metadata": metadata
        })
        
        # Check for sequence violations
        await self._check_event_sequence(thread_id, event_type)
        
        # Calculate latency if we have previous events
        if len(self.event_history[thread_id]) > 1:
            prev_event = self.event_history[thread_id][-2]
            latency = now - prev_event["timestamp"]
            self.event_latencies.append(latency)
            
            # Trim latency samples
            if len(self.event_latencies) > self.max_latency_samples:
                self.event_latencies = self.event_latencies[-self.max_latency_samples:]
            
            # Check for high latency
            if latency > self.latency_critical_threshold:
                logger.critical(
                    f"CRITICAL LATENCY: {latency:.2f}s between events in thread {thread_id}"
                )
            elif latency > self.latency_warning_threshold:
                logger.warning(
                    f"High latency: {latency:.2f}s between events in thread {thread_id}"
                )
    
    async def _check_event_sequence(self, thread_id: str, event_type: str) -> None:
        """Check if event follows expected sequence."""
        expected = self.expected_sequences.get(thread_id, [])
        
        if expected and event_type not in expected:
            # Unexpected event - potential silent failure
            await self._record_silent_failure(
                thread_id,
                f"Unexpected event {event_type}, expected one of: {expected}",
                {"received": event_type, "expected": expected}
            )
    
    async def _record_silent_failure(
        self, 
        thread_id: str, 
        reason: str,
        details: Optional[Dict] = None
    ) -> None:
        """Record a detected silent failure."""
        failure = {
            "thread_id": thread_id,
            "reason": reason,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        self.silent_failures.append(failure)
        
        # Trim old failures
        if len(self.silent_failures) > self.max_silent_failures:
            self.silent_failures = self.silent_failures[-self.max_silent_failures:]
        
        # Log critical issue
        logger.critical(
            f"SILENT FAILURE DETECTED in thread {thread_id}: {reason}. "
            f"Details: {details}"
        )
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check system health and return status report.
        
        Returns comprehensive health status including:
        - Overall health status
        - Stale threads
        - Stuck tools
        - Silent failures
        - Latency metrics
        """
        now = time.time()
        issues = []
        metrics = {}
        
        # Check for stale threads
        stale_threads = []
        for thread_id in self.thread_start_time:
            last_event_key = None
            last_time = 0
            
            # Find most recent event for this thread
            for event_type in EventType:
                key = f"{thread_id}:{event_type.value}"
                if key in self.last_event_time:
                    if self.last_event_time[key] > last_time:
                        last_time = self.last_event_time[key]
                        last_event_key = key
            
            if last_time > 0 and (now - last_time) > self.stale_thread_threshold:
                stale_threads.append({
                    "thread_id": thread_id,
                    "last_event": last_event_key,
                    "seconds_stale": now - last_time
                })
                issues.append(f"Thread {thread_id} stale for {now - last_time:.1f}s")
        
        # Check for stuck tools
        stuck_tools = []
        for thread_id, tools in self.active_tools.items():
            for tool in tools:
                # Find when tool started executing
                for event in reversed(self.event_history.get(thread_id, [])):
                    if (event["event_type"] == EventType.TOOL_EXECUTING.value and 
                        event.get("tool_name") == tool):
                        tool_duration = now - event["timestamp"]
                        if tool_duration > self.tool_timeout_threshold:
                            stuck_tools.append({
                                "thread_id": thread_id,
                                "tool_name": tool,
                                "duration": tool_duration
                            })
                            issues.append(
                                f"Tool {tool} stuck in thread {thread_id} for {tool_duration:.1f}s"
                            )
                        break
        
        # Calculate latency metrics
        if self.event_latencies:
            avg_latency = sum(self.event_latencies) / len(self.event_latencies)
            max_latency = max(self.event_latencies)
            min_latency = min(self.event_latencies)
            
            metrics["avg_latency"] = avg_latency
            metrics["max_latency"] = max_latency
            metrics["min_latency"] = min_latency
            
            if avg_latency > self.latency_warning_threshold:
                issues.append(f"High average latency: {avg_latency:.2f}s")
        
        # Determine overall health
        if not issues and not self.silent_failures:
            status = HealthStatus.HEALTHY
        elif len(issues) <= 2 and len(self.silent_failures) <= 5:
            status = HealthStatus.WARNING
        elif len(issues) <= 5 and len(self.silent_failures) <= 10:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.FAILED
        
        return {
            "status": status.value,
            "healthy": status == HealthStatus.HEALTHY,
            "issues": issues,
            "stale_threads": stale_threads,
            "stuck_tools": stuck_tools,
            "silent_failures": self.silent_failures[-10:],  # Last 10 failures
            "metrics": metrics,
            "active_threads": len(self.thread_start_time),
            "total_events": sum(
                sum(counts.values()) for counts in self.event_counts.values()
            )
        }
    
    async def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Chat event monitor started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring task."""
        self._shutdown = True
        if self._monitor_task:
            await self._monitor_task
            self._monitor_task = None
            logger.info("Chat event monitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown:
            try:
                # Check health every 10 seconds
                await asyncio.sleep(10)
                
                health_report = await self.check_health()
                
                if health_report["status"] == HealthStatus.FAILED.value:
                    logger.critical(
                        f"CHAT SYSTEM FAILED: {len(health_report['issues'])} issues detected. "
                        f"Silent failures: {len(health_report['silent_failures'])}"
                    )
                elif health_report["status"] == HealthStatus.CRITICAL.value:
                    logger.error(
                        f"Chat system critical: {health_report['issues']}"
                    )
                elif health_report["status"] == HealthStatus.WARNING.value:
                    logger.warning(
                        f"Chat system warning: {health_report['issues']}"
                    )
                
                # Clean up old thread data (older than 1 hour)
                cutoff_time = time.time() - 3600
                threads_to_remove = []
                
                for thread_id, start_time in self.thread_start_time.items():
                    if start_time < cutoff_time:
                        # Check if thread has recent activity
                        has_recent_activity = False
                        for event_type in EventType:
                            key = f"{thread_id}:{event_type.value}"
                            if key in self.last_event_time:
                                if self.last_event_time[key] > cutoff_time:
                                    has_recent_activity = True
                                    break
                        
                        if not has_recent_activity:
                            threads_to_remove.append(thread_id)
                
                # Clean up old threads
                for thread_id in threads_to_remove:
                    self._cleanup_thread(thread_id)
                    
            except Exception as e:
                logger.error(f"Error in event monitor loop: {e}")
    
    def _cleanup_thread(self, thread_id: str) -> None:
        """Clean up data for an old thread."""
        self.thread_start_time.pop(thread_id, None)
        self.event_counts.pop(thread_id, None)
        self.active_tools.pop(thread_id, None)
        self.expected_sequences.pop(thread_id, None)
        self.event_history.pop(thread_id, None)
        
        # Clean up event times
        keys_to_remove = []
        for key in self.last_event_time:
            if key.startswith(f"{thread_id}:"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.last_event_time.pop(key, None)
    
    def get_thread_status(self, thread_id: str) -> Dict[str, Any]:
        """Get detailed status for a specific thread."""
        if thread_id not in self.thread_start_time:
            return {"status": "unknown", "thread_id": thread_id}
        
        now = time.time()
        thread_age = now - self.thread_start_time[thread_id]
        
        # Get event counts
        events = self.event_counts.get(thread_id, {})
        
        # Get last event
        last_event = None
        last_time = 0
        for event in self.event_history.get(thread_id, []):
            if event["timestamp"] > last_time:
                last_time = event["timestamp"]
                last_event = event
        
        # Check for active tools
        active_tools = list(self.active_tools.get(thread_id, set()))
        
        return {
            "thread_id": thread_id,
            "age_seconds": thread_age,
            "event_counts": dict(events),
            "last_event": last_event,
            "active_tools": active_tools,
            "total_events": sum(events.values()),
            "status": "active" if (now - last_time) < self.stale_thread_threshold else "stale"
        }


# Global monitor instance
chat_event_monitor = ChatEventMonitor()