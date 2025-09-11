"""Coordination Health Monitor - Real-time multi-layer coordination tracking.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Foundation for all real-time features
- Business Goal: Monitor and ensure multi-layer coordination health
- Value Impact: Prevents silent coordination failures affecting user experience
- Strategic Impact: CRITICAL - Protects $500K+ ARR Golden Path reliability

This module provides real-time monitoring and alerting for coordination health
between WebSocket, Database, Agent, and Cache layers to ensure system integrity.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class CoordinationLayer(Enum):
    """Layers involved in multi-layer coordination."""
    WEBSOCKET = "websocket"
    DATABASE = "database"
    AGENT = "agent"
    CACHE = "cache"
    USER_CONTEXT = "user_context"


class HealthStatus(Enum):
    """Health status levels for coordination monitoring."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class CoordinationEvent:
    """Represents a coordination event between system layers."""
    event_id: str
    event_type: str
    layers: List[CoordinationLayer]
    timing_data: Dict[str, float]  # layer -> timestamp
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HealthAlert:
    """Health alert for coordination issues."""
    alert_id: str
    event_type: str
    health_status: HealthStatus
    affected_layers: List[CoordinationLayer]
    timing_gaps: Dict[str, float]
    error_message: str
    user_impact: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None


class CoordinationHealthMonitor:
    """Monitor and track multi-layer coordination health.
    
    This monitor tracks coordination events between different system layers
    and provides real-time health metrics, alerting, and issue resolution.
    """
    
    def __init__(self, alert_thresholds: Optional[Dict[str, float]] = None):
        """Initialize coordination health monitor.
        
        Args:
            alert_thresholds: Custom thresholds for health alerts
        """
        # Default health thresholds (in milliseconds)
        self.health_thresholds = {
            'websocket_db_gap': 100.0,      # WebSocket events should follow DB commits within 100ms
            'agent_state_sync': 50.0,       # Agent state updates should sync within 50ms
            'transaction_boundary': 5.0,    # Transaction boundaries should be respected within 5ms
            'cache_db_sync': 25.0,          # Cache and DB should sync within 25ms
            'user_context_isolation': 1.0,  # User context isolation should be immediate
            'rollback_notification': 200.0  # Rollback notifications within 200ms
        }
        
        # Override with custom thresholds if provided
        if alert_thresholds:
            self.health_thresholds.update(alert_thresholds)
            
        # Monitoring data
        self.coordination_events: List[CoordinationEvent] = []
        self.health_alerts: List[HealthAlert] = []
        self.health_metrics: Dict[str, List[float]] = defaultdict(list)
        self.layer_performance: Dict[CoordinationLayer, Dict[str, Any]] = defaultdict(dict)
        
        # Performance tracking
        self._event_count = 0
        self._alert_count = 0
        self._monitoring_start_time = datetime.now(timezone.utc)
        
        # Health monitoring configuration
        self._monitoring_enabled = True
        self._alert_callbacks: List[callable] = []
        self._metrics_window_minutes = 60  # Keep metrics for 1 hour
        self._max_events_stored = 10000    # Limit memory usage
        
        logger.info("🏥 CoordinationHealthMonitor initialized with thresholds: %s", self.health_thresholds)
        
    async def track_coordination_event(self, event_type: str, layers: List[CoordinationLayer], 
                                     timing_data: Dict[str, float], user_id: Optional[str] = None,
                                     thread_id: Optional[str] = None, transaction_id: Optional[str] = None,
                                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Track a coordination event with timing analysis.
        
        Args:
            event_type: Type of coordination event
            layers: List of layers involved in the event
            timing_data: Dictionary mapping layer names to timestamps
            user_id: Optional user ID for context
            thread_id: Optional thread ID for context
            transaction_id: Optional transaction ID for context
            metadata: Optional additional metadata
            
        Returns:
            Event ID for tracking purposes
        """
        if not self._monitoring_enabled:
            return ""
            
        event_id = f"coord_event_{uuid.uuid4().hex[:8]}"
        
        # Create coordination event
        event = CoordinationEvent(
            event_id=event_id,
            event_type=event_type,
            layers=layers,
            timing_data=timing_data,
            user_id=user_id,
            thread_id=thread_id,
            transaction_id=transaction_id,
            metadata=metadata or {}
        )
        
        # Store event (with memory management)
        self.coordination_events.append(event)
        self._event_count += 1
        
        # Limit stored events to prevent memory growth
        if len(self.coordination_events) > self._max_events_stored:
            self.coordination_events = self.coordination_events[-self._max_events_stored//2:]
            logger.debug("🧹 Trimmed coordination events to manage memory")
            
        # Calculate timing gaps and evaluate health
        timing_gaps = self._calculate_timing_gaps(timing_data)
        health_status = self._evaluate_health(event_type, timing_gaps)
        
        # Store health metrics
        for gap_type, gap_value in timing_gaps.items():
            self.health_metrics[gap_type].append(gap_value)
            
        # Update layer performance tracking
        self._update_layer_performance(layers, timing_data, timing_gaps)
        
        # Generate alerts if health is poor
        if health_status in [HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.FAILED]:
            await self._generate_health_alert(event, health_status, timing_gaps)
            
        logger.debug(f"📊 Tracked coordination event {event_id}: {event_type} "
                    f"(layers: {[l.value for l in layers]}, health: {health_status.value})")
        
        return event_id
        
    def _calculate_timing_gaps(self, timing_data: Dict[str, float]) -> Dict[str, float]:
        """Calculate timing gaps between layers.
        
        Args:
            timing_data: Dictionary mapping layer names to timestamps
            
        Returns:
            Dictionary mapping gap types to gap values (in milliseconds)
        """
        gaps = {}
        
        # Convert to milliseconds for easier threshold comparison
        timestamps_ms = {layer: ts * 1000 for layer, ts in timing_data.items()}
        
        # Calculate specific layer gaps
        if 'database' in timestamps_ms and 'websocket' in timestamps_ms:
            # WebSocket events should come AFTER database commits
            gap = timestamps_ms['websocket'] - timestamps_ms['database']
            gaps['websocket_db_gap'] = gap
            
        if 'agent' in timestamps_ms and 'database' in timestamps_ms:
            # Agent state updates coordination with database
            gap = abs(timestamps_ms['agent'] - timestamps_ms['database'])
            gaps['agent_state_sync'] = gap
            
        if 'cache' in timestamps_ms and 'database' in timestamps_ms:
            # Cache and database synchronization
            gap = abs(timestamps_ms['cache'] - timestamps_ms['database'])
            gaps['cache_db_sync'] = gap
            
        if 'user_context' in timestamps_ms:
            # User context operations should be immediate (minimal gap)
            other_layers = [layer for layer in timestamps_ms.keys() if layer != 'user_context']
            if other_layers:
                max_gap = max(abs(timestamps_ms['user_context'] - timestamps_ms[layer]) 
                             for layer in other_layers)
                gaps['user_context_isolation'] = max_gap
                
        # Calculate overall coordination span
        if len(timestamps_ms) > 1:
            max_time = max(timestamps_ms.values())
            min_time = min(timestamps_ms.values())
            gaps['coordination_span'] = max_time - min_time
            
        return gaps
        
    def _evaluate_health(self, event_type: str, timing_gaps: Dict[str, float]) -> HealthStatus:
        """Evaluate coordination health based on timing gaps.
        
        Args:
            event_type: Type of coordination event
            timing_gaps: Calculated timing gaps
            
        Returns:
            HealthStatus indicating overall coordination health
        """
        violations = []
        critical_violations = []
        
        for gap_type, gap_value in timing_gaps.items():
            threshold = self.health_thresholds.get(gap_type, float('inf'))
            
            if gap_value > threshold:
                if gap_value > threshold * 2:  # Critical if 2x threshold
                    critical_violations.append((gap_type, gap_value, threshold))
                else:
                    violations.append((gap_type, gap_value, threshold))
                    
        # Determine health status
        if critical_violations:
            return HealthStatus.CRITICAL
        elif len(violations) >= 2:  # Multiple violations = critical
            return HealthStatus.CRITICAL
        elif violations:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
            
    def _update_layer_performance(self, layers: List[CoordinationLayer], 
                                timing_data: Dict[str, float], timing_gaps: Dict[str, float]):
        """Update performance metrics for each layer.
        
        Args:
            layers: Layers involved in the event
            timing_data: Raw timing data
            timing_gaps: Calculated timing gaps
        """
        current_time = datetime.now(timezone.utc)
        
        for layer in layers:
            if layer not in self.layer_performance:
                self.layer_performance[layer] = {
                    'total_events': 0,
                    'avg_response_time': 0.0,
                    'max_response_time': 0.0,
                    'violations': 0,
                    'last_event_time': current_time
                }
                
            perf = self.layer_performance[layer]
            perf['total_events'] += 1
            perf['last_event_time'] = current_time
            
            # Update response time metrics if available
            layer_time = timing_data.get(layer.value, 0)
            if layer_time > 0:
                perf['max_response_time'] = max(perf['max_response_time'], layer_time)
                # Simple moving average
                perf['avg_response_time'] = (perf['avg_response_time'] + layer_time) / 2
                
            # Count violations for this layer
            layer_violations = sum(1 for gap_type in timing_gaps.keys() 
                                 if layer.value in gap_type and 
                                 timing_gaps[gap_type] > self.health_thresholds.get(gap_type, float('inf')))
            perf['violations'] += layer_violations
            
    async def _generate_health_alert(self, event: CoordinationEvent, health_status: HealthStatus, 
                                   timing_gaps: Dict[str, float]):
        """Generate and process health alert for coordination issues.
        
        Args:
            event: Coordination event that triggered the alert
            health_status: Determined health status
            timing_gaps: Timing gaps that caused the alert
        """
        alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        
        # Determine affected layers and user impact
        affected_layers = event.layers
        user_impact = self._assess_user_impact(event.event_type, health_status, timing_gaps)
        
        # Create detailed error message
        violation_details = []
        for gap_type, gap_value in timing_gaps.items():
            threshold = self.health_thresholds.get(gap_type, float('inf'))
            if gap_value > threshold:
                violation_details.append(f"{gap_type}: {gap_value:.1f}ms (threshold: {threshold:.1f}ms)")
                
        error_message = (f"Coordination health issue in {event.event_type}: "
                        f"{', '.join(violation_details)}")
        
        # Create health alert
        alert = HealthAlert(
            alert_id=alert_id,
            event_type=event.event_type,
            health_status=health_status,
            affected_layers=affected_layers,
            timing_gaps=timing_gaps.copy(),
            error_message=error_message,
            user_impact=user_impact
        )
        
        self.health_alerts.append(alert)
        self._alert_count += 1
        
        # Log alert based on severity
        if health_status == HealthStatus.CRITICAL:
            logger.critical(f"🚨 CRITICAL coordination health alert {alert_id}: {error_message}")
        elif health_status == HealthStatus.WARNING:
            logger.warning(f"⚠️ WARNING coordination health alert {alert_id}: {error_message}")
            
        logger.info(f"📊 Alert {alert_id} - User impact: {user_impact}")
        
        # Call registered alert callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"❌ Alert callback failed for {alert_id}: {e}")
                
    def _assess_user_impact(self, event_type: str, health_status: HealthStatus, 
                          timing_gaps: Dict[str, float]) -> str:
        """Assess the impact of coordination issues on user experience.
        
        Args:
            event_type: Type of coordination event
            health_status: Current health status
            timing_gaps: Timing gaps causing the issue
            
        Returns:
            Description of user impact
        """
        if health_status == HealthStatus.HEALTHY:
            return "No user impact"
            
        # Determine impact based on event type and gaps
        impacts = []
        
        if 'websocket_db_gap' in timing_gaps and timing_gaps['websocket_db_gap'] > 100:
            impacts.append("Users may see inconsistent data updates")
            
        if 'agent_state_sync' in timing_gaps and timing_gaps['agent_state_sync'] > 50:
            impacts.append("Agent responses may be delayed or inconsistent")
            
        if 'transaction_boundary' in timing_gaps and timing_gaps['transaction_boundary'] > 5:
            impacts.append("Data consistency issues possible")
            
        if 'rollback_notification' in timing_gaps and timing_gaps['rollback_notification'] > 200:
            impacts.append("Users may not be notified of operation failures")
            
        if not impacts:
            if health_status == HealthStatus.CRITICAL:
                impacts.append("Severe coordination issues affecting system reliability")
            else:
                impacts.append("Minor coordination delays affecting responsiveness")
                
        return "; ".join(impacts)
        
    def get_health_score(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get current coordination health score.
        
        Args:
            time_window_minutes: Time window for health calculation
            
        Returns:
            Dictionary containing health score and metrics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        
        # Get recent events
        recent_events = [e for e in self.coordination_events if e.created_at > cutoff_time]
        recent_alerts = [a for a in self.health_alerts if a.created_at > cutoff_time]
        
        if not recent_events:
            return {
                "overall_health_score": 100.0,
                "status": "healthy",
                "events_analyzed": 0,
                "alerts_generated": 0,
                "message": "No coordination events in time window"
            }
            
        # Calculate health score based on alerts vs events
        total_events = len(recent_events)
        critical_alerts = len([a for a in recent_alerts if a.health_status == HealthStatus.CRITICAL])
        warning_alerts = len([a for a in recent_alerts if a.health_status == HealthStatus.WARNING])
        
        # Health score calculation (0-100)
        health_score = 100.0
        health_score -= (critical_alerts / total_events) * 50  # Critical alerts heavily penalize
        health_score -= (warning_alerts / total_events) * 20   # Warning alerts moderately penalize
        health_score = max(0.0, health_score)
        
        # Determine overall status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "critical"
            
        # Calculate layer-specific scores
        layer_scores = {}
        for layer in CoordinationLayer:
            layer_events = [e for e in recent_events if layer in e.layers]
            layer_alerts = [a for a in recent_alerts if layer in a.affected_layers]
            
            if layer_events:
                layer_score = 100.0 - (len(layer_alerts) / len(layer_events)) * 60
                layer_scores[layer.value] = max(0.0, layer_score)
            else:
                layer_scores[layer.value] = 100.0
                
        return {
            "overall_health_score": round(health_score, 1),
            "status": status,
            "events_analyzed": total_events,
            "alerts_generated": len(recent_alerts),
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "layer_scores": layer_scores,
            "time_window_minutes": time_window_minutes,
            "monitoring_uptime_hours": (datetime.now(timezone.utc) - self._monitoring_start_time).total_seconds() / 3600
        }
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all layers.
        
        Returns:
            Dictionary containing performance metrics by layer
        """
        metrics = {}
        
        for layer, perf_data in self.layer_performance.items():
            metrics[layer.value] = {
                "total_events": perf_data.get('total_events', 0),
                "average_response_time_ms": round(perf_data.get('avg_response_time', 0) * 1000, 2),
                "max_response_time_ms": round(perf_data.get('max_response_time', 0) * 1000, 2),
                "violation_count": perf_data.get('violations', 0),
                "last_event_time": perf_data.get('last_event_time', datetime.now(timezone.utc)).isoformat()
            }
            
        return metrics
        
    def add_alert_callback(self, callback: callable):
        """Add callback function for health alerts.
        
        Args:
            callback: Async function to call when alerts are generated
        """
        self._alert_callbacks.append(callback)
        logger.debug(f"📞 Added alert callback: {callback.__name__}")
        
    def set_monitoring_enabled(self, enabled: bool):
        """Enable or disable coordination monitoring.
        
        Args:
            enabled: Whether to enable monitoring
        """
        self._monitoring_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🏥 Coordination health monitoring {status}")
        
    async def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old monitoring data to manage memory.
        
        Args:
            max_age_hours: Maximum age of data to keep
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Clean up old events
        old_event_count = len(self.coordination_events)
        self.coordination_events = [e for e in self.coordination_events if e.created_at > cutoff_time]
        
        # Clean up old alerts
        old_alert_count = len(self.health_alerts)
        self.health_alerts = [a for a in self.health_alerts if a.created_at > cutoff_time]
        
        # Clean up old metrics
        for metric_type in list(self.health_metrics.keys()):
            # Keep only recent metrics (simple time-based cleanup)
            recent_size = max(100, len(self.health_metrics[metric_type]) // 2)
            self.health_metrics[metric_type] = self.health_metrics[metric_type][-recent_size:]
            
        events_cleaned = old_event_count - len(self.coordination_events)
        alerts_cleaned = old_alert_count - len(self.health_alerts)
        
        if events_cleaned > 0 or alerts_cleaned > 0:
            logger.info(f"🧹 Cleaned up old monitoring data: {events_cleaned} events, {alerts_cleaned} alerts")
            
        return events_cleaned + alerts_cleaned
        
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and configuration.
        
        Returns:
            Dictionary containing monitoring status information
        """
        return {
            "monitoring_enabled": self._monitoring_enabled,
            "uptime_hours": (datetime.now(timezone.utc) - self._monitoring_start_time).total_seconds() / 3600,
            "total_events_tracked": self._event_count,
            "total_alerts_generated": self._alert_count,
            "current_events_stored": len(self.coordination_events),
            "current_alerts_stored": len(self.health_alerts),
            "health_thresholds": self.health_thresholds,
            "metrics_window_minutes": self._metrics_window_minutes,
            "max_events_stored": self._max_events_stored,
            "alert_callbacks_registered": len(self._alert_callbacks)
        }