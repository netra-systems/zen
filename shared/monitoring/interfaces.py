"""Monitoring interface definitions for component health auditing.

Business Value: Enables independent monitoring integration where any component
can be monitored without tight coupling, supporting comprehensive failure detection.

Architecture: 
- MonitorableComponent: Interface for components that can be monitored
- ComponentMonitor: Interface for monitors that observe components  
- Observer pattern with graceful degradation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from shared.monitoring.interfaces import ComponentMonitor

class MonitorableComponent(ABC):
    """
    Interface for components that can be monitored/audited by external monitors.
    
    Design Principles:
    - Components remain fully independent (work without monitors)
    - Standardized monitoring contract across all components
    - Observer pattern for health change notifications
    - Graceful degradation if monitoring integration fails
    
    Business Value:
    - Enables comprehensive system health visibility
    - Supports silent failure detection
    - Provides operational metrics for business decisions
    """
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status for monitoring.
        
        Must return a standardized health status dictionary containing:
        - Basic health indicators (healthy/unhealthy)
        - Component state information  
        - Error conditions if any
        - Timestamp of health check
        
        Returns:
            Dict containing health status with standard keys:
            - 'healthy': bool indicating overall health
            - 'state': str describing current state
            - 'timestamp': float unix timestamp of check
            - component-specific health indicators
            
        Raises:
            Exception: If health check fails (monitor should handle gracefully)
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get operational metrics for analysis and business decisions.
        
        Must return metrics relevant for:
        - Performance monitoring
        - Capacity planning
        - Business impact assessment
        - Debugging and troubleshooting
        
        Returns:
            Dict containing operational metrics:
            - Counters (total operations, failures, successes)
            - Rates (success rate, throughput)
            - Timing metrics (average response time, uptime)
            - Component-specific metrics
            
        Raises:
            Exception: If metrics collection fails (monitor should handle gracefully)
        """
        pass
    
    @abstractmethod
    def register_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Register a monitor to observe this component's health changes.
        
        Implementation should:
        - Store observer reference for health change notifications
        - Handle duplicate registrations gracefully
        - Continue normal operation if observer registration fails
        - Log observer registration for debugging
        
        Args:
            observer: Monitor that will receive health change notifications
            
        Note:
            Component must remain fully functional even if no observers registered
        """
        pass
    
    def remove_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Remove a registered monitor observer.
        
        Optional method with default implementation for observer cleanup.
        Components may override for custom cleanup logic.
        
        Args:
            observer: Monitor to remove from notifications
        """
        # Default implementation - components may override
        pass
    
    async def notify_health_change(self, health_data: Dict[str, Any]) -> None:
        """
        Notify all registered observers of health status changes.
        
        Default implementation handles observer notification with error resilience.
        Components may override but should maintain error handling.
        
        Args:
            health_data: Current health status data to broadcast
        """
        # Default implementation - components may override
        # This would be implemented in concrete components with observer list
        pass


class ComponentMonitor(ABC):
    """
    Interface for monitors that observe and audit components.
    
    Design Principles:
    - Monitor operates independently of observed components
    - Handles component failures gracefully
    - Provides cross-validation capabilities
    - Maintains audit history for analysis
    
    Business Value:
    - Enables comprehensive failure detection
    - Provides business impact assessment
    - Supports operational decision making
    """
    
    @abstractmethod
    async def register_component_for_monitoring(
        self, 
        component_id: str, 
        component: MonitorableComponent
    ) -> None:
        """
        Register a component for monitoring and auditing.
        
        Args:
            component_id: Unique identifier for the component
            component: Component instance to monitor
            
        Raises:
            Exception: If registration fails (should not stop monitor operation)
        """
        pass
    
    @abstractmethod
    async def on_component_health_change(
        self, 
        component_id: str, 
        health_data: Dict[str, Any]
    ) -> None:
        """
        Handle health change notification from a monitored component.
        
        Args:
            component_id: ID of component reporting health change
            health_data: Current health status data
        """
        pass
    
    async def remove_component_from_monitoring(self, component_id: str) -> None:
        """
        Remove a component from monitoring.
        
        Optional method with default implementation.
        Monitors may override for custom cleanup.
        
        Args:
            component_id: ID of component to stop monitoring
        """
        # Default implementation - monitors may override
        pass


class HealthStatus:
    """
    Standardized health status representation for consistent reporting.
    
    Provides common health status structure that all components can use
    for consistent monitoring integration.
    """
    
    def __init__(
        self,
        healthy: bool,
        state: str,
        timestamp: Optional[float] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize health status.
        
        Args:
            healthy: Overall health indicator
            state: Descriptive state (e.g., "running", "degraded", "failed")
            timestamp: Unix timestamp of status check
            error_message: Error description if unhealthy
            details: Additional component-specific details
        """
        self.healthy = healthy
        self.state = state
        self.timestamp = timestamp or time.time()
        self.error_message = error_message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.healthy,
            "state": self.state,
            "timestamp": self.timestamp,
            "error_message": self.error_message,
            "details": self.details
        }
    
    @classmethod
    def healthy_status(cls, state: str = "running", **kwargs) -> "HealthStatus":
        """Create a healthy status instance."""
        return cls(healthy=True, state=state, **kwargs)
    
    @classmethod
    def unhealthy_status(
        cls, 
        state: str = "failed", 
        error: str = "Component unhealthy",
        **kwargs
    ) -> "HealthStatus":
        """Create an unhealthy status instance."""
        return cls(healthy=False, state=state, error_message=error, **kwargs)


class MonitoringMetrics:
    """
    Standardized metrics collection helper for consistent reporting.
    
    Provides common metrics structure that components can use for
    consistent monitoring integration.
    """
    
    def __init__(self):
        """Initialize metrics collection."""
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = {}
        self.timestamps: Dict[str, float] = {}
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.counters[name] = self.counters.get(name, 0) + value
        self.timestamps[f"{name}_last_update"] = time.time()
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        self.gauges[name] = value
        self.timestamps[f"{name}_last_update"] = time.time()
    
    def record_timer(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        if name not in self.timers:
            self.timers[name] = []
        self.timers[name].append(duration)
        # Keep last 1000 measurements
        if len(self.timers[name]) > 1000:
            self.timers[name] = self.timers[name][-1000:]
        self.timestamps[f"{name}_last_update"] = time.time()
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        return self.gauges.get(name, 0.0)
    
    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get timer statistics."""
        measurements = self.timers.get(name, [])
        if not measurements:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": len(measurements),
            "avg": sum(measurements) / len(measurements),
            "min": min(measurements),
            "max": max(measurements)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all metrics to dictionary."""
        result = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timestamps": dict(self.timestamps)
        }
        
        # Add timer statistics
        timer_stats = {}
        for name in self.timers:
            timer_stats[name] = self.get_timer_stats(name)
        result["timers"] = timer_stats
        
        return result