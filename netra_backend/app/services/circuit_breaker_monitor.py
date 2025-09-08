"""Circuit breaker monitoring and alerting system.

This module provides comprehensive monitoring, metrics collection,
and alerting for circuit breaker state changes across the platform.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.circuit_breaker import CircuitState, circuit_registry
from netra_backend.app.core.resilience.monitor import AlertSeverity
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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
    
    def _is_already_monitoring(self) -> bool:
        """Check if monitoring is already active"""
        if self._monitoring_active:
            logger.warning("Circuit breaker monitoring already active")
            return True
        return False

    def _start_monitor_task(self, interval_seconds: float) -> None:
        """Start the monitoring task"""
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        # Add done callback to retrieve exceptions and prevent "Task exception was never retrieved"
        self._monitor_task.add_done_callback(
            lambda t: logger.error(f"Circuit breaker monitoring failed: {t.exception()}") 
            if t.exception() else logger.info("Circuit breaker monitoring task completed")
        )
        logger.info(f"Circuit breaker monitoring started (interval: {interval_seconds}s)")

    async def start_monitoring(self, interval_seconds: float = 5.0) -> None:
        """Start continuous circuit breaker monitoring."""
        if self._is_already_monitoring():
            return
        self._start_monitor_task(interval_seconds)
    
    async def _cancel_monitor_task(self) -> None:
        """Cancel the monitoring task"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def stop_monitoring(self) -> None:
        """Stop circuit breaker monitoring."""
        self._monitoring_active = False
        await self._cancel_monitor_task()
        logger.info("Circuit breaker monitoring stopped")
    
    async def _monitor_iteration(self, interval_seconds: float) -> None:
        """Single monitoring iteration"""
        try:
            await self._check_circuit_states()
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Circuit breaker monitoring error: {e}")
            await asyncio.sleep(interval_seconds)

    async def _monitor_loop(self, interval_seconds: float) -> None:
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self._monitor_iteration(interval_seconds)
            except asyncio.CancelledError:
                break
    
    async def _check_circuit_states(self) -> None:
        """Check all circuit breaker states for changes."""
        all_status = await circuit_registry.get_all_status()
        
        for circuit_name, status in all_status.items():
            await self._process_circuit_status(circuit_name, status)
    
    def _get_circuit_states(self, circuit_name: str, status: Dict[str, Any]) -> tuple[str, str]:
        """Get current and old states for circuit"""
        current_state = status.get("state", "unknown")
        old_state = self._last_states.get(circuit_name, "unknown")
        return current_state, old_state

    async def _process_state_change(self, circuit_name: str, old_state: str, current_state: str, status: Dict[str, Any]) -> None:
        """Process circuit state change if needed"""
        if old_state != current_state:
            await self._handle_state_change(circuit_name, old_state, current_state, status)

    async def _process_circuit_status(self, circuit_name: str, status: Dict[str, Any]) -> None:
        """Process individual circuit status."""
        current_state, old_state = self._get_circuit_states(circuit_name, status)
        await self._process_state_change(circuit_name, old_state, current_state, status)
        await self._check_alerts(circuit_name, status)
        self._last_states[circuit_name] = current_state
    
    def _record_state_change_event(self, circuit_name: str, old_state: str, new_state: str, status: Dict[str, Any]) -> None:
        """Record state change event"""
        from netra_backend.app.services.circuit_breaker_helpers import create_state_change_event
        event = create_state_change_event(circuit_name, old_state, new_state, status)
        self._events.append(event)
        self._trim_events()
        logger.info(f"Circuit breaker state change: {circuit_name} {old_state} -> {new_state}")

    async def _handle_circuit_open_alert(self, circuit_name: str, new_state: str, status: Dict[str, Any]) -> None:
        """Handle alert creation for circuit open state"""
        from netra_backend.app.services.circuit_breaker_helpers import should_create_open_circuit_alert
        if should_create_open_circuit_alert(new_state):
            await self._create_open_circuit_alert(circuit_name, new_state, status)

    async def _handle_state_change(self, 
                                  circuit_name: str, 
                                  old_state: str, 
                                  new_state: str,
                                  status: Dict[str, Any]) -> None:
        """Handle circuit breaker state change."""
        self._record_state_change_event(circuit_name, old_state, new_state, status)
        await self._handle_circuit_open_alert(circuit_name, new_state, status)
    
    async def _create_open_circuit_alert(self, circuit_name: str, new_state: str, status: Dict[str, Any]) -> None:
        """Create alert for opened circuit breaker."""
        message = "Circuit breaker OPENED due to failures"
        metrics = status.get("metrics", {})
        await self._create_alert(circuit_name, AlertSeverity.HIGH, message, new_state, metrics)
    
    async def _check_alerts(self, circuit_name: str, status: Dict[str, Any]) -> None:
        """Check for alert conditions."""
        from netra_backend.app.services.circuit_breaker_helpers import extract_circuit_metrics
        metrics_data = extract_circuit_metrics(status)
        await self._check_success_rate_alert(circuit_name, metrics_data)
        await self._check_rejection_rate_alert(circuit_name, metrics_data)
    
    async def _check_success_rate_alert(self, circuit_name: str, metrics_data: Dict[str, Any]) -> None:
        """Check and create low success rate alert if needed."""
        from netra_backend.app.services.circuit_breaker_helpers import should_alert_low_success_rate
        if should_alert_low_success_rate(metrics_data["state"], metrics_data["success_rate"], metrics_data["total_calls"]):
            await self._create_alert(circuit_name, AlertSeverity.MEDIUM, f"Low success rate: {metrics_data['success_rate']:.2%}", metrics_data["state"], {"total_calls": metrics_data["total_calls"]})
    
    async def _check_rejection_rate_alert(self, circuit_name: str, metrics_data: Dict[str, Any]) -> None:
        """Check and create high rejection rate alert if needed."""
        from .circuit_breaker_helpers import (
            calculate_rejection_rate,
            should_alert_high_rejection_rate,
        )
        rejection_rate = calculate_rejection_rate(metrics_data["rejected_calls"], metrics_data["total_calls"])
        if should_alert_high_rejection_rate(rejection_rate, metrics_data["rejected_calls"]):
            await self._create_alert(circuit_name, AlertSeverity.HIGH, f"High rejection rate: {rejection_rate:.2%}", metrics_data["state"], {"rejected_calls": metrics_data["rejected_calls"]})
    
    def _build_alert(self, circuit_name: str, severity: AlertSeverity, message: str, state: str, metrics: Dict[str, Any]) -> CircuitBreakerAlert:
        """Build circuit breaker alert"""
        return CircuitBreakerAlert(
            circuit_name=circuit_name, severity=severity, message=message,
            timestamp=datetime.now(UTC), state=state, metrics=metrics
        )

    def _store_alert(self, alert: CircuitBreakerAlert) -> None:
        """Store alert and trim list"""
        self._alerts.append(alert)
        self._trim_alerts()

    async def _dispatch_alert_to_handlers(self, alert: CircuitBreakerAlert) -> None:
        """Dispatch alert to all handlers"""
        for handler in self._alert_handlers:
            try:
                # No need to create_task for awaiting - just await directly to prevent race conditions
                await self._call_handler(handler, alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    async def _create_alert(self, circuit_name: str, severity: AlertSeverity, message: str, 
                           state: str, metrics: Dict[str, Any]) -> None:
        """Create and dispatch alert."""
        alert = self._build_alert(circuit_name, severity, message, state, metrics)
        self._store_alert(alert)
        await self._dispatch_alert_to_handlers(alert)
    
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
        from .circuit_breaker_helpers import (
            build_health_summary_base,
            populate_health_summary,
        )
        summary = build_health_summary_base()
        recent_events_count = len(self.get_recent_events(10))
        recent_alerts_count = len(self.get_recent_alerts(10))
        populate_health_summary(summary, self._last_states, recent_events_count, recent_alerts_count)
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
        from netra_backend.app.services.circuit_breaker_helpers import extract_metrics_from_status
        return extract_metrics_from_status(status, timestamp)
    
    def _store_metrics(self, circuit_name: str, metrics: Dict[str, Any]) -> None:
        """Store metrics with history trimming."""
        from .circuit_breaker_helpers import (
            initialize_circuit_history,
            trim_metrics_history,
        )
        initialize_circuit_history(self._metrics_history, circuit_name)
        self._metrics_history[circuit_name].append(metrics)
        self._metrics_history[circuit_name] = trim_metrics_history(self._metrics_history[circuit_name])
    
    def get_metrics_history(self, circuit_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for circuit."""
        if circuit_name not in self._metrics_history:
            return []
        
        from netra_backend.app.services.circuit_breaker_helpers import filter_metrics_by_time
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return filter_metrics_by_time(self._metrics_history[circuit_name], cutoff_time)
    
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
        
        from .circuit_breaker_helpers import (
            build_aggregated_metrics,
            calculate_aggregated_totals,
        )
        total_calls, success_rates = calculate_aggregated_totals(history)
        return build_aggregated_metrics(total_calls, success_rates, history)


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
    from netra_backend.app.services.circuit_breaker_helpers import build_alert_data, build_event_data
    health_summary = circuit_monitor.get_health_summary()
    recent_events = circuit_monitor.get_recent_events(20)
    recent_alerts = circuit_monitor.get_recent_alerts(10)
    aggregated_metrics = metrics_collector.get_aggregated_metrics(1)
    return _build_dashboard_response(health_summary, recent_events, recent_alerts, aggregated_metrics)


def _build_dashboard_response(health_summary, recent_events, recent_alerts, aggregated_metrics) -> Dict[str, Any]:
    """Build dashboard response dictionary."""
    from netra_backend.app.services.circuit_breaker_helpers import build_alert_data, build_event_data
    event_data = build_event_data(recent_events)
    alert_data = build_alert_data(recent_alerts)
    return _create_dashboard_dict(health_summary, event_data, alert_data, aggregated_metrics)


def _create_dashboard_dict(health_summary, event_data, alert_data, aggregated_metrics) -> Dict[str, Any]:
    """Create dashboard dictionary with all components."""
    return {
        "summary": health_summary,
        "recent_events": event_data,
        "recent_alerts": alert_data,
        "metrics": aggregated_metrics
    }