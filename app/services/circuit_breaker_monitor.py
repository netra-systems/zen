"""Circuit breaker monitoring and alerting system.

This module provides comprehensive monitoring, metrics collection,
and alerting for circuit breaker state changes across the platform.
"""

import asyncio
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.core.circuit_breaker import circuit_registry, CircuitState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker state change event."""
    circuit_name: str
    old_state: str
    new_state: str
    timestamp: datetime
    failure_count: int
    success_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerAlert:
    """Circuit breaker alert."""
    circuit_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    state: str
    metrics: Dict[str, Any] = field(default_factory=dict)


class CircuitBreakerMonitor:
    """Monitor circuit breaker health and performance."""
    
    def __init__(self):
        self._last_states: Dict[str, str] = {}
        self._events: List[CircuitBreakerEvent] = []
        self._alerts: List[CircuitBreakerAlert] = []
        self._alert_handlers: List[Callable[[CircuitBreakerAlert], None]] = []
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def add_alert_handler(self, handler: Callable[[CircuitBreakerAlert], None]) -> None:
        """Add alert handler for notifications."""
        self._alert_handlers.append(handler)
    
    async def start_monitoring(self, interval_seconds: float = 5.0) -> None:
        """Start continuous circuit breaker monitoring."""
        if self._monitoring_active:
            logger.warning("Circuit breaker monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval_seconds)
        )
        logger.info(f"Circuit breaker monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop circuit breaker monitoring."""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Circuit breaker monitoring stopped")
    
    async def _monitor_loop(self, interval_seconds: float) -> None:
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self._check_circuit_states()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Circuit breaker monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def _check_circuit_states(self) -> None:
        """Check all circuit breaker states for changes."""
        all_status = await circuit_registry.get_all_status()
        
        for circuit_name, status in all_status.items():
            await self._process_circuit_status(circuit_name, status)
    
    async def _process_circuit_status(self, circuit_name: str, status: Dict[str, Any]) -> None:
        """Process individual circuit status."""
        current_state = status.get("state", "unknown")
        old_state = self._last_states.get(circuit_name, "unknown")
        
        # Check for state changes
        if old_state != current_state:
            await self._handle_state_change(circuit_name, old_state, current_state, status)
        
        # Check for alerts based on current status
        await self._check_alerts(circuit_name, status)
        
        self._last_states[circuit_name] = current_state
    
    async def _handle_state_change(self, 
                                  circuit_name: str, 
                                  old_state: str, 
                                  new_state: str,
                                  status: Dict[str, Any]) -> None:
        """Handle circuit breaker state change."""
        from .circuit_breaker_helpers import create_state_change_event, should_create_open_circuit_alert
        event = create_state_change_event(circuit_name, old_state, new_state, status)
        self._events.append(event)
        self._trim_events()
        logger.info(f"Circuit breaker state change: {circuit_name} {old_state} -> {new_state}")
        
        if should_create_open_circuit_alert(new_state):
            await self._create_open_circuit_alert(circuit_name, new_state, status)
    
    async def _create_open_circuit_alert(self, circuit_name: str, new_state: str, status: Dict[str, Any]) -> None:
        """Create alert for opened circuit breaker."""
        await self._create_alert(
            circuit_name=circuit_name,
            severity=AlertSeverity.HIGH,
            message=f"Circuit breaker OPENED due to failures",
            state=new_state,
            metrics=status.get("metrics", {})
        )
    
    async def _check_alerts(self, circuit_name: str, status: Dict[str, Any]) -> None:
        """Check for alert conditions."""
        from .circuit_breaker_helpers import extract_circuit_metrics
        metrics_data = extract_circuit_metrics(status)
        await self._check_success_rate_alert(circuit_name, metrics_data)
        await self._check_rejection_rate_alert(circuit_name, metrics_data)
    
    async def _check_success_rate_alert(self, circuit_name: str, metrics_data: Dict[str, Any]) -> None:
        """Check and create low success rate alert if needed."""
        from .circuit_breaker_helpers import should_alert_low_success_rate
        if should_alert_low_success_rate(metrics_data["state"], metrics_data["success_rate"], metrics_data["total_calls"]):
            await self._create_alert(circuit_name, AlertSeverity.MEDIUM, f"Low success rate: {metrics_data['success_rate']:.2%}", metrics_data["state"], {"total_calls": metrics_data["total_calls"]})
    
    async def _check_rejection_rate_alert(self, circuit_name: str, metrics_data: Dict[str, Any]) -> None:
        """Check and create high rejection rate alert if needed."""
        from .circuit_breaker_helpers import calculate_rejection_rate, should_alert_high_rejection_rate
        rejection_rate = calculate_rejection_rate(metrics_data["rejected_calls"], metrics_data["total_calls"])
        if should_alert_high_rejection_rate(rejection_rate, metrics_data["rejected_calls"]):
            await self._create_alert(circuit_name, AlertSeverity.HIGH, f"High rejection rate: {rejection_rate:.2%}", metrics_data["state"], {"rejected_calls": metrics_data["rejected_calls"]})
    
    async def _create_alert(self, 
                           circuit_name: str,
                           severity: AlertSeverity,
                           message: str,
                           state: str,
                           metrics: Dict[str, Any]) -> None:
        """Create and dispatch alert."""
        alert = CircuitBreakerAlert(
            circuit_name=circuit_name,
            severity=severity,
            message=message,
            timestamp=datetime.now(UTC),
            state=state,
            metrics=metrics
        )
        
        self._alerts.append(alert)
        self._trim_alerts()
        
        # Dispatch to handlers
        for handler in self._alert_handlers:
            try:
                await asyncio.create_task(self._call_handler(handler, alert))
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    async def _call_handler(self, handler: Callable, alert: CircuitBreakerAlert) -> None:
        """Call alert handler safely."""
        if asyncio.iscoroutinefunction(handler):
            await handler(alert)
        else:
            handler(alert)
    
    def _trim_events(self, max_events: int = 1000) -> None:
        """Trim events list to prevent memory growth."""
        if len(self._events) > max_events:
            self._events = self._events[-max_events:]
    
    def _trim_alerts(self, max_alerts: int = 500) -> None:
        """Trim alerts list to prevent memory growth."""
        if len(self._alerts) > max_alerts:
            self._alerts = self._alerts[-max_alerts:]
    
    def get_recent_events(self, limit: int = 50) -> List[CircuitBreakerEvent]:
        """Get recent circuit breaker events."""
        return self._events[-limit:]
    
    def get_recent_alerts(self, limit: int = 50) -> List[CircuitBreakerAlert]:
        """Get recent alerts."""
        return self._alerts[-limit:]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all circuits."""
        from .circuit_breaker_helpers import build_health_summary_base, categorize_circuit_state
        summary = build_health_summary_base()
        summary["total_circuits"] = len(self._last_states)
        summary["recent_events"] = len(self.get_recent_events(10))
        summary["recent_alerts"] = len(self.get_recent_alerts(10))
        
        for state in self._last_states.values():
            category = categorize_circuit_state(state)
            summary[f"{category}_circuits"] += 1
        
        return summary


class CircuitBreakerMetricsCollector:
    """Collect and aggregate circuit breaker metrics."""
    
    def __init__(self):
        self._metrics_history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def collect_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Collect current metrics from all circuits."""
        all_status = await circuit_registry.get_all_status()
        timestamp = datetime.now(UTC)
        
        for circuit_name, status in all_status.items():
            metrics = self._extract_metrics(status, timestamp)
            self._store_metrics(circuit_name, metrics)
        
        return all_status
    
    def _extract_metrics(self, status: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        """Extract key metrics from circuit status."""
        return {
            "timestamp": timestamp,
            "state": status.get("state", "unknown"),
            "success_rate": status.get("success_rate", 0.0),
            "failure_count": status.get("failure_count", 0),
            "total_calls": status.get("metrics", {}).get("total_calls", 0),
            "rejected_calls": status.get("metrics", {}).get("rejected_calls", 0),
            "timeouts": status.get("metrics", {}).get("timeouts", 0)
        }
    
    def _store_metrics(self, circuit_name: str, metrics: Dict[str, Any]) -> None:
        """Store metrics with history trimming."""
        if circuit_name not in self._metrics_history:
            self._metrics_history[circuit_name] = []
        
        self._metrics_history[circuit_name].append(metrics)
        
        # Keep last 1000 entries
        if len(self._metrics_history[circuit_name]) > 1000:
            self._metrics_history[circuit_name] = self._metrics_history[circuit_name][-1000:]
    
    def get_metrics_history(self, circuit_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for circuit."""
        if circuit_name not in self._metrics_history:
            return []
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [
            m for m in self._metrics_history[circuit_name]
            if m["timestamp"] >= cutoff_time
        ]
    
    def get_aggregated_metrics(self, hours: int = 1) -> Dict[str, Dict[str, Any]]:
        """Get aggregated metrics for all circuits."""
        aggregated = {}
        
        for circuit_name in self._metrics_history.keys():
            history = self.get_metrics_history(circuit_name, hours)
            if history:
                aggregated[circuit_name] = self._aggregate_history(history)
        
        return aggregated
    
    def _aggregate_history(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics history."""
        if not history:
            return {}
        
        total_calls = sum(m.get("total_calls", 0) for m in history)
        success_rates = [m.get("success_rate", 0.0) for m in history if m.get("total_calls", 0) > 0]
        
        return {
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0.0,
            "total_calls": total_calls,
            "total_rejections": sum(m.get("rejected_calls", 0) for m in history),
            "total_timeouts": sum(m.get("timeouts", 0) for m in history),
            "state_changes": len(set(m.get("state", "unknown") for m in history)) - 1
        }


# Global monitoring instances
circuit_monitor = CircuitBreakerMonitor()
metrics_collector = CircuitBreakerMetricsCollector()


async def default_alert_handler(alert: CircuitBreakerAlert) -> None:
    """Default alert handler that logs alerts."""
    logger.warning(
        f"Circuit Breaker Alert [{alert.severity.value.upper()}] "
        f"{alert.circuit_name}: {alert.message} (state: {alert.state})"
    )


# Set up default alert handler
circuit_monitor.add_alert_handler(default_alert_handler)


async def get_circuit_health_dashboard() -> Dict[str, Any]:
    """Get comprehensive circuit breaker health dashboard."""
    health_summary = circuit_monitor.get_health_summary()
    recent_events = circuit_monitor.get_recent_events(20)
    recent_alerts = circuit_monitor.get_recent_alerts(10)
    aggregated_metrics = metrics_collector.get_aggregated_metrics(1)
    
    return {
        "summary": health_summary,
        "recent_events": [
            {
                "circuit": event.circuit_name,
                "transition": f"{event.old_state} -> {event.new_state}",
                "timestamp": event.timestamp.isoformat(),
                "success_rate": event.success_rate
            }
            for event in recent_events
        ],
        "recent_alerts": [
            {
                "circuit": alert.circuit_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in recent_alerts
        ],
        "metrics": aggregated_metrics
    }