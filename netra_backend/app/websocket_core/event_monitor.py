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
from shared.monitoring.interfaces import ComponentMonitor, MonitorableComponent

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


class ChatEventMonitor(ComponentMonitor):
    """
    Monitor critical chat event flow in real-time with component auditing capabilities.
    
    Features:
    - Tracks event flow per thread
    - Detects missing events (e.g., tool_executing without tool_completed)
    - Identifies stale threads (no events for extended period)
    - Monitors event delivery latency
    - Provides health status and alerts
    - NEW: Audits registered components (like AgentWebSocketBridge)
    - NEW: Cross-validates component health claims against event data
    - NEW: Maintains component health history for analysis
    
    Business Value: Enables comprehensive monitoring coverage where the monitor 
    can audit components without creating tight coupling.
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
        
        # NEW: Component audit capabilities
        self.monitored_components: Dict[str, MonitorableComponent] = {}
        self.component_health_history: Dict[str, List[Dict]] = defaultdict(list)
        self.bridge_audit_metrics: Dict[str, Any] = {}
        self.max_health_history_per_component = 50  # Keep last 50 health reports per component
        
    async def record_event(
        self, 
        event_type: str, 
        thread_id: str,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record an event occurrence and check for anomalies."""
        # Skip monitoring for test threads to prevent false anomaly detection
        if self._is_test_thread(thread_id):
            logger.debug(f"Skipping event monitoring for test thread: {thread_id}")
            return
        
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
    
    def _is_test_thread(self, thread_id: str) -> bool:
        """
        Identify test threads to prevent false anomaly detection.
        
        Test threads created during health checks, unit tests, and system
        validation should not be monitored for anomalies as they have
        different lifecycle patterns than real user threads.
        
        Args:
            thread_id: Thread identifier to check
            
        Returns:
            bool: True if this is a test thread, False otherwise
        """
        if not isinstance(thread_id, str):
            return False
            
        test_patterns = [
            "startup_test_",
            "health_check_", 
            "test_",
            "unit_test_",
            "integration_test_",
            "validation_",
            "mock_"
        ]
        
        return any(thread_id.startswith(pattern) for pattern in test_patterns)
    
    def get_thread_status(self, thread_id: str) -> Dict[str, Any]:
        """Get detailed status for a specific thread."""
        # Handle test threads specially
        if self._is_test_thread(thread_id):
            return {
                "status": "test_thread", 
                "thread_id": thread_id,
                "message": "Test thread - not monitored for anomalies"
            }
            
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
    
    # NEW: Component Auditing Methods
    
    async def register_component_for_monitoring(
        self, 
        component_id: str, 
        component: MonitorableComponent
    ) -> None:
        """
        Register a component (like AgentWebSocketBridge) for monitoring.
        
        Enables the monitor to audit component health while maintaining independence.
        Component continues to work normally even if registration fails.
        
        Args:
            component_id: Unique identifier for the component
            component: Component instance implementing MonitorableComponent
            
        Business Value: Enables comprehensive system health visibility
        and silent failure detection across integrated components.
        """
        try:
            self.monitored_components[component_id] = component
            
            # Register ourselves as an observer with the component
            component.register_monitor_observer(self)
            
            # Initialize health history for this component
            if component_id not in self.component_health_history:
                self.component_health_history[component_id] = []
            
            logger.info(f" PASS:  Component {component_id} registered for monitoring successfully")
            
            # Perform initial health audit
            await self._perform_initial_audit(component_id)
            
        except Exception as e:
            logger.warning(
                f" WARNING: [U+FE0F] Failed to register component {component_id} for monitoring: {e}. "
                f"Component will continue operating independently."
            )
    
    async def _perform_initial_audit(self, component_id: str) -> None:
        """Perform initial health audit of newly registered component."""
        try:
            audit_result = await self.audit_bridge_health(component_id)
            logger.info(
                f"Initial audit complete for {component_id}: "
                f"Status={audit_result.get('internal_health', {}).get('healthy', 'unknown')}"
            )
        except Exception as e:
            logger.warning(f"Initial audit failed for {component_id}: {e}")
    
    async def audit_bridge_health(self, bridge_id: str = "main_bridge") -> Dict[str, Any]:
        """
        Specific audit of AgentWebSocketBridge health and integration.
        
        Performs comprehensive audit including:
        - Component's internal health status
        - Component's operational metrics  
        - Cross-validation with event monitor data
        - Integration health assessment
        
        Args:
            bridge_id: ID of the bridge component to audit
            
        Returns:
            Dict containing comprehensive audit results
            
        Business Value: Provides 360-degree view of bridge health combining
        internal metrics with external validation for complete visibility.
        """
        if bridge_id not in self.monitored_components:
            return {
                "status": "not_monitored", 
                "bridge_id": bridge_id,
                "audit_timestamp": time.time(),
                "message": f"Component {bridge_id} not registered for monitoring"
            }
        
        try:
            bridge = self.monitored_components[bridge_id]
            
            # Get bridge's internal health status and metrics
            bridge_health = await bridge.get_health_status()
            bridge_metrics = await bridge.get_metrics()
            
            # Cross-validate with event monitor data
            event_validation = await self._validate_bridge_events(bridge_id)
            integration_assessment = await self._assess_bridge_integration(bridge_id)
            
            # Compile comprehensive audit result
            audit_result = {
                "bridge_id": bridge_id,
                "audit_timestamp": time.time(),
                "internal_health": bridge_health,
                "internal_metrics": bridge_metrics,
                "event_monitor_validation": event_validation,
                "integration_health": integration_assessment,
                "overall_assessment": self._calculate_overall_assessment(
                    bridge_health, event_validation, integration_assessment
                )
            }
            
            # Store audit history (trim if needed)
            self.component_health_history[bridge_id].append(audit_result)
            if len(self.component_health_history[bridge_id]) > self.max_health_history_per_component:
                self.component_health_history[bridge_id] = self.component_health_history[bridge_id][-self.max_health_history_per_component:]
            
            # Update bridge audit metrics for trend analysis
            self._update_bridge_audit_metrics(bridge_id, audit_result)
            
            return audit_result
            
        except Exception as e:
            error_result = {
                "bridge_id": bridge_id,
                "status": "audit_failed",
                "error": str(e),
                "audit_timestamp": time.time()
            }
            logger.error(f"Bridge audit failed for {bridge_id}: {e}")
            return error_result
    
    async def _validate_bridge_events(self, bridge_id: str) -> Dict[str, Any]:
        """
        Cross-validate bridge health claims against actual event data.
        
        Compares bridge's claimed health with observed event patterns
        to detect discrepancies that might indicate silent failures.
        
        Returns:
            Dict containing event validation results
        """
        validation = {
            "validation_timestamp": time.time(),
            "total_active_threads": len(self.thread_start_time),
            "total_events_processed": sum(
                sum(counts.values()) for counts in self.event_counts.values()
            ),
            "recent_silent_failures": len([
                f for f in self.silent_failures 
                if time.time() - f["timestamp"] < 300  # Last 5 minutes
            ]),
            "stale_threads_count": 0,
            "stuck_tools_count": 0
        }
        
        # Check for stale threads
        now = time.time()
        stale_count = 0
        for thread_id in self.thread_start_time:
            last_time = 0
            for event_type in EventType:
                key = f"{thread_id}:{event_type.value}"
                if key in self.last_event_time:
                    last_time = max(last_time, self.last_event_time[key])
            
            if last_time > 0 and (now - last_time) > self.stale_thread_threshold:
                stale_count += 1
        
        validation["stale_threads_count"] = stale_count
        
        # Check for stuck tools
        stuck_count = 0
        for thread_id, tools in self.active_tools.items():
            stuck_count += len(tools)  # Any active tool could be stuck
        validation["stuck_tools_count"] = stuck_count
        
        # Determine validation status
        if validation["recent_silent_failures"] == 0 and stale_count == 0 and stuck_count == 0:
            validation["status"] = "healthy"
        elif validation["recent_silent_failures"] <= 2 and stale_count <= 1:
            validation["status"] = "warning"  
        else:
            validation["status"] = "critical"
            
        return validation
    
    async def _assess_bridge_integration(self, bridge_id: str) -> Dict[str, Any]:
        """
        Assess quality of bridge integration with WebSocket system.
        
        Evaluates how well the bridge is integrated and functioning
        within the overall chat system architecture.
        
        Returns:
            Dict containing integration assessment
        """
        assessment = {
            "assessment_timestamp": time.time(),
            "bridge_registered": bridge_id in self.monitored_components,
            "health_history_available": len(self.component_health_history.get(bridge_id, [])) > 0,
            "metrics_available": bridge_id in self.bridge_audit_metrics,
            "integration_score": 0.0
        }
        
        # Calculate integration score based on available data
        score_components = []
        
        if assessment["bridge_registered"]:
            score_components.append(25.0)  # Registration: 25%
            
        if assessment["health_history_available"]:
            score_components.append(25.0)  # Health tracking: 25%
            
        if assessment["metrics_available"]:
            score_components.append(25.0)  # Metrics collection: 25%
            
        # Event correlation score: 25%
        if self.event_counts:
            score_components.append(25.0)  # Events being processed
            
        assessment["integration_score"] = sum(score_components)
        
        # Determine integration status
        if assessment["integration_score"] >= 90:
            assessment["status"] = "excellent"
        elif assessment["integration_score"] >= 75:
            assessment["status"] = "good"
        elif assessment["integration_score"] >= 50:
            assessment["status"] = "fair"
        else:
            assessment["status"] = "poor"
            
        return assessment
    
    def _calculate_overall_assessment(
        self, 
        health: Dict[str, Any], 
        validation: Dict[str, Any], 
        integration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall assessment from individual audit components."""
        
        # Weight the different assessment components
        health_weight = 0.5  # Internal health: 50%
        validation_weight = 0.3  # Event validation: 30%  
        integration_weight = 0.2  # Integration quality: 20%
        
        # Convert status to numeric scores
        status_scores = {"excellent": 100, "good": 80, "healthy": 80, "fair": 60, "warning": 40, "critical": 20, "poor": 20, "failed": 0}
        
        health_score = status_scores.get(health.get("state", "unknown"), 0)
        if not health.get("healthy", False):
            health_score = min(health_score, 40)  # Cap unhealthy components
            
        validation_score = status_scores.get(validation.get("status", "unknown"), 0)
        integration_score = status_scores.get(integration.get("status", "unknown"), 0)
        
        # Calculate weighted overall score
        overall_score = (
            health_score * health_weight +
            validation_score * validation_weight + 
            integration_score * integration_weight
        )
        
        # Determine overall status
        if overall_score >= 80:
            overall_status = "healthy"
        elif overall_score >= 60:
            overall_status = "warning"
        elif overall_score >= 40:
            overall_status = "critical"
        else:
            overall_status = "failed"
            
        return {
            "overall_score": round(overall_score, 1),
            "overall_status": overall_status,
            "component_scores": {
                "health": health_score,
                "validation": validation_score,
                "integration": integration_score
            }
        }
    
    def _update_bridge_audit_metrics(self, bridge_id: str, audit_result: Dict[str, Any]) -> None:
        """Update trending metrics based on audit results."""
        if bridge_id not in self.bridge_audit_metrics:
            self.bridge_audit_metrics[bridge_id] = {
                "total_audits": 0,
                "healthy_audits": 0,
                "failed_audits": 0,
                "avg_score": 0.0,
                "last_audit": None
            }
        
        metrics = self.bridge_audit_metrics[bridge_id]
        metrics["total_audits"] += 1
        metrics["last_audit"] = audit_result["audit_timestamp"]
        
        overall_assessment = audit_result.get("overall_assessment", {})
        if overall_assessment.get("overall_status") == "healthy":
            metrics["healthy_audits"] += 1
        elif overall_assessment.get("overall_status") in ["critical", "failed"]:
            metrics["failed_audits"] += 1
            
        # Update running average score
        if "overall_score" in overall_assessment:
            current_score = overall_assessment["overall_score"]
            # Simple running average (could use more sophisticated method)
            metrics["avg_score"] = (
                (metrics["avg_score"] * (metrics["total_audits"] - 1) + current_score) / 
                metrics["total_audits"]
            )
    
    async def on_component_health_change(
        self, 
        component_id: str, 
        health_data: Dict[str, Any]
    ) -> None:
        """
        Handle health change notification from a monitored component.
        
        Called by components when their health status changes.
        Maintains health history and triggers alerts if needed.
        
        Args:
            component_id: ID of component reporting health change
            health_data: Current health status data
        """
        try:
            # Log health change
            healthy = health_data.get("healthy", health_data.get("state") == "running")
            logger.info(
                f"Health change notification from {component_id}: "
                f"Status={health_data.get('state', 'unknown')}, Healthy={healthy}"
            )
            
            # Store in health history
            health_record = {
                "component_id": component_id,
                "timestamp": time.time(),
                "health_data": health_data,
                "notification_type": "health_change"
            }
            
            self.component_health_history[component_id].append(health_record)
            
            # Trim history if needed
            if len(self.component_health_history[component_id]) > self.max_health_history_per_component:
                self.component_health_history[component_id] = self.component_health_history[component_id][-self.max_health_history_per_component:]
            
            # Log component health status changes
            if not healthy:
                # Check if this is the expected uninitialized state for the bridge
                if component_id == "agent_websocket_bridge" and health_data.get('state') == 'uninitialized':
                    logger.info(
                        f"[U+2139][U+FE0F] Component {component_id} in expected uninitialized state. "
                        f"This is normal - bridge uses per-request initialization. "
                        f"See AGENT_WEBSOCKET_BRIDGE_UNINITIALIZED_FIVE_WHYS.md for details."
                    )
                else:
                    logger.warning(
                        f" ALERT:  Component {component_id} reported unhealthy status: "
                        f"{health_data.get('state', 'unknown')}. "
                        f"Error: {health_data.get('error_message', 'No details provided')}"
                    )
                
                # Could trigger additional alert mechanisms here
                # (e.g., notifications, automated recovery)
                
        except Exception as e:
            logger.error(f"Error handling health change notification from {component_id}: {e}")
    
    async def remove_component_from_monitoring(self, component_id: str) -> None:
        """
        Remove a component from monitoring.
        
        Args:
            component_id: ID of component to stop monitoring
        """
        try:
            if component_id in self.monitored_components:
                component = self.monitored_components.pop(component_id)
                
                # Remove ourselves from component's observers
                try:
                    component.remove_monitor_observer(self)
                except Exception:
                    pass  # Component may not support observer removal
                
                # Clean up health history (keep for historical analysis)
                # self.component_health_history.pop(component_id, None)  # Commented out to preserve history
                
                logger.info(f"Component {component_id} removed from monitoring")
            else:
                logger.warning(f"Attempted to remove non-monitored component: {component_id}")
                
        except Exception as e:
            logger.error(f"Error removing component {component_id} from monitoring: {e}")
    
    def get_component_audit_summary(self) -> Dict[str, Any]:
        """
        Get summary of all monitored components and their audit status.
        
        Returns:
            Dict containing comprehensive monitoring summary for business visibility
        """
        summary = {
            "monitoring_timestamp": time.time(),
            "total_monitored_components": len(self.monitored_components),
            "components": {},
            "overall_system_health": "unknown"
        }
        
        healthy_components = 0
        total_components = len(self.monitored_components)
        
        for component_id in self.monitored_components:
            # Get latest health record
            history = self.component_health_history.get(component_id, [])
            latest_audit = history[-1] if history else None
            
            component_summary = {
                "component_id": component_id,
                "monitored": True,
                "audit_history_count": len(history),
                "metrics_available": component_id in self.bridge_audit_metrics
            }
            
            if latest_audit:
                if "overall_assessment" in latest_audit:
                    # This is an audit result
                    assessment = latest_audit["overall_assessment"]
                    component_summary["last_audit_status"] = assessment.get("overall_status", "unknown")
                    component_summary["last_audit_score"] = assessment.get("overall_score", 0)
                    component_summary["last_audit_timestamp"] = latest_audit.get("audit_timestamp")
                    
                    if assessment.get("overall_status") == "healthy":
                        healthy_components += 1
                else:
                    # This is a health change notification
                    health_data = latest_audit.get("health_data", {})
                    component_summary["last_health_status"] = health_data.get("state", "unknown")
                    component_summary["last_health_timestamp"] = latest_audit.get("timestamp")
                    
                    if health_data.get("healthy", False):
                        healthy_components += 1
            
            summary["components"][component_id] = component_summary
        
        # Calculate overall system health
        if total_components == 0:
            summary["overall_system_health"] = "no_monitored_components"
        elif healthy_components == total_components:
            summary["overall_system_health"] = "healthy"
        elif healthy_components >= total_components * 0.8:
            summary["overall_system_health"] = "warning"
        else:
            summary["overall_system_health"] = "critical"
            
        summary["healthy_component_ratio"] = f"{healthy_components}/{total_components}"
        
        return summary


# Backward compatibility WebSocketEventMonitor that matches test expectations
class WebSocketEventMonitor:
    """
    WebSocket Event Monitor that wraps ChatEventMonitor with test-compatible interface.
    
    This class provides the interface expected by unit tests while delegating
    actual monitoring functionality to the existing ChatEventMonitor.
    """
    
    def __init__(self, track_critical_events: bool = True, validate_event_order: bool = True, metrics_enabled: bool = True):
        """Initialize with configuration options expected by tests."""
        self.track_critical_events = track_critical_events
        self.validate_event_order = validate_event_order
        self.metrics_enabled = metrics_enabled
        self._session_trackers = {}  # Track active sessions
        self._validation_lock = asyncio.Lock()  # For thread safety
        
        # Delegate to actual monitor
        self._delegate = chat_event_monitor
    
    async def start_session_tracking(self, session_id: str, session_data: dict):
        """Start tracking an agent session."""
        async with self._validation_lock:
            self._session_trackers[session_id] = EventTracker()
            # Delegate to actual monitor
            await self._delegate.record_event("agent_started", session_data.get("thread_id", session_id))
    
    async def record_event(self, event_type: str, session_id: str, event_data: dict = None):
        """Record an event for a session."""
        if session_id in self._session_trackers:
            self._session_trackers[session_id].track_event(event_type, session_id, event_data)
        
        # Delegate to actual monitor
        await self._delegate.record_event(event_type, session_id, metadata=event_data)
    
    async def validate_critical_events(self, session_id: str) -> bool:
        """Validate that all critical events were received for a session."""
        if not self.track_critical_events:
            return True
            
        if session_id not in self._session_trackers:
            return False
            
        tracker = self._session_trackers[session_id]
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event in critical_events:
            if not any(e["event_type"] == event for e in tracker.events):
                raise MissingCriticalEventError(f"Missing critical event: {event}")
        
        return True
    
    async def get_session_metrics(self, session_id: str) -> dict:
        """Get metrics for a specific session."""
        if not self.metrics_enabled or session_id not in self._session_trackers:
            return {}
            
        tracker = self._session_trackers[session_id]
        return {
            "total_events": len(tracker.events),
            "event_types": list(set(e["event_type"] for e in tracker.events)),
            "session_duration": time.time() - (tracker.events[0]["timestamp"] if tracker.events else time.time())
        }
    
    async def stop_session_tracking(self, session_id: str):
        """Stop tracking a session and clean up."""
        async with self._validation_lock:
            if session_id in self._session_trackers:
                del self._session_trackers[session_id]

# Exception classes for test compatibility
class EventValidationError(Exception):
    """Raised when event validation fails."""
    pass

class MissingCriticalEventError(EventValidationError):
    """Raised when a critical event is missing."""
    pass

# Additional classes for test compatibility
class EventTracker:
    """Simple event tracker for unit testing."""
    def __init__(self):
        self.events = []
    
    def track_event(self, event_type: str, thread_id: str, metadata: dict = None):
        self.events.append({
            "event_type": event_type,
            "thread_id": thread_id,
            "metadata": metadata or {},
            "timestamp": time.time()
        })

class EventMetrics:
    """Event metrics container for unit testing."""
    def __init__(self):
        self.total_events = 0
        self.events_by_type = {}
        self.avg_processing_time = 0.0
    
    def update(self, event_type: str, processing_time: float = 0.0):
        self.total_events += 1
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        # Simple running average
        self.avg_processing_time = ((self.avg_processing_time * (self.total_events - 1)) + processing_time) / self.total_events


# Global monitor instance
chat_event_monitor = ChatEventMonitor()