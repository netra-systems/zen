"""Base monitoring interfaces for component health and integration auditing.

This module implements the core monitoring interfaces required for issue #1019
- integrating ChatEventMonitor with AgentWebSocketBridge.

Business Value: Enables comprehensive monitoring of critical chat infrastructure
components to prevent silent failures that could impact $500K+ ARR.

Architecture: Provides standardized interfaces for component monitoring that
support both internal health tracking and external audit capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
import time
import asyncio
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.event_monitor import ComponentMonitor

logger = central_logger.get_logger(__name__)


class MonitorableComponent(ABC):
    """
    Enhanced interface for components that can be monitored by external systems.
    
    Extends the base monitoring interface with additional capabilities specifically
    needed for ChatEventMonitor integration and WebSocket health auditing.
    
    Design Principles:
    - Components remain fully independent (work without monitors)
    - Standardized monitoring contract across all components
    - Observer pattern for health change notifications
    - Graceful degradation if monitoring integration fails
    - Enhanced audit capabilities for business-critical components
    
    Business Value:
    - Enables comprehensive system health visibility
    - Supports silent failure detection
    - Provides operational metrics for business decisions
    - Protects chat functionality reliability
    """
    
    def __init__(self):
        """Initialize monitoring capabilities with observer management."""
        self._monitor_observers = []
        self._health_history = []
        self._max_health_history = 50
        self._monitoring_enabled = True
        
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status for monitoring.
        
        Enhanced implementation must return comprehensive health data including:
        - Basic health indicators (healthy/unhealthy)
        - Component state information  
        - Error conditions if any
        - Timestamp of health check
        - Integration status with dependent systems
        - Performance metrics affecting health
        
        Returns:
            Dict containing enhanced health status with standard keys:
            - 'healthy': bool indicating overall health
            - 'state': str describing current state
            - 'timestamp': float unix timestamp of check
            - 'integration_health': dict of dependent system statuses
            - 'performance_indicators': dict of performance metrics
            - 'error_message': str if unhealthy
            - component-specific health indicators
            
        Raises:
            Exception: If health check fails (monitor should handle gracefully)
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get operational metrics for analysis and business decisions.
        
        Enhanced implementation must return metrics relevant for:
        - Performance monitoring and alerting
        - Capacity planning and scaling decisions
        - Business impact assessment
        - Debugging and troubleshooting
        - Integration health with other components
        
        Returns:
            Dict containing comprehensive operational metrics:
            - Counters (total operations, failures, successes)
            - Rates (success rate, throughput, error rates)
            - Timing metrics (average response time, uptime, latency)
            - Integration metrics (dependency health, connection status)
            - Component-specific metrics for business analysis
            
        Raises:
            Exception: If metrics collection fails (monitor should handle gracefully)
        """
        pass
    
    def register_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Register a monitor to observe this component's health changes.
        
        Enhanced implementation provides robust observer management with:
        - Duplicate registration prevention
        - Error handling for failed registrations
        - Logging for audit trails
        - Graceful degradation if observer communication fails
        
        Args:
            observer: Monitor that will receive health change notifications
            
        Note:
            Component must remain fully functional even if no observers registered
        """
        try:
            if observer not in self._monitor_observers:
                self._monitor_observers.append(observer)
                logger.info(f"Monitor observer registered successfully: {type(observer).__name__}")
            else:
                logger.debug(f"Monitor observer already registered: {type(observer).__name__}")
                
        except Exception as e:
            logger.warning(
                f"Failed to register monitor observer {type(observer).__name__}: {e}. "
                f"Component will continue operating without this monitor."
            )
    
    def remove_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Remove a registered monitor observer.
        
        Enhanced implementation with safe removal and error handling.
        
        Args:
            observer: Monitor to remove from notifications
        """
        try:
            if observer in self._monitor_observers:
                self._monitor_observers.remove(observer)
                logger.info(f"Monitor observer removed successfully: {type(observer).__name__}")
            else:
                logger.debug(f"Monitor observer not found for removal: {type(observer).__name__}")
                
        except Exception as e:
            logger.warning(f"Error removing monitor observer {type(observer).__name__}: {e}")
    
    async def notify_health_change(self, health_data: Dict[str, Any]) -> None:
        """
        Notify all registered observers of health status changes.
        
        Enhanced implementation with:
        - Resilient error handling for each observer
        - Health history tracking for trend analysis
        - Performance monitoring of notification delivery
        - Graceful handling of unresponsive observers
        
        Args:
            health_data: Current health status data to broadcast
        """
        if not self._monitoring_enabled:
            return
            
        try:
            # Store health data in history for trend analysis
            self._store_health_history(health_data)
            
            # Notify all observers with individual error handling
            notification_tasks = []
            for observer in self._monitor_observers.copy():  # Copy to avoid modification during iteration
                task = self._notify_single_observer(observer, health_data)
                notification_tasks.append(task)
            
            # Execute notifications concurrently with timeout
            if notification_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*notification_tasks, return_exceptions=True),
                        timeout=5.0  # 5 second timeout for observer notifications
                    )
                except asyncio.TimeoutError:
                    logger.warning("Health change notification timeout - some observers may be unresponsive")
                    
        except Exception as e:
            logger.error(f"Error in health change notification: {e}")
    
    async def _notify_single_observer(self, observer: 'ComponentMonitor', health_data: Dict[str, Any]) -> None:
        """Notify a single observer with error isolation."""
        try:
            # Generate component ID for observer notification
            component_id = getattr(self, 'component_id', self.__class__.__name__.lower())
            await observer.on_component_health_change(component_id, health_data)
            
        except Exception as e:
            logger.warning(
                f"Failed to notify observer {type(observer).__name__} of health change: {e}. "
                f"Observer may be unresponsive but component continues operating."
            )
    
    def _store_health_history(self, health_data: Dict[str, Any]) -> None:
        """Store health data in history with size management."""
        try:
            health_record = {
                'timestamp': time.time(),
                'health_data': health_data.copy(),
                'component_type': self.__class__.__name__
            }
            
            self._health_history.append(health_record)
            
            # Trim history to maintain size limit
            if len(self._health_history) > self._max_health_history:
                self._health_history = self._health_history[-self._max_health_history:]
                
        except Exception as e:
            logger.warning(f"Error storing health history: {e}")
    
    def get_health_history(self) -> list:
        """Get component health history for trend analysis."""
        return self._health_history.copy()
    
    def enable_monitoring(self) -> None:
        """Enable monitoring and observer notifications."""
        self._monitoring_enabled = True
        logger.info(f"Monitoring enabled for {self.__class__.__name__}")
    
    def disable_monitoring(self) -> None:
        """Disable monitoring and observer notifications."""
        self._monitoring_enabled = False
        logger.info(f"Monitoring disabled for {self.__class__.__name__}")
    
    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is currently enabled."""
        return self._monitoring_enabled


class EnhancedComponentMonitor(ABC):
    """
    Enhanced interface for monitors that observe and audit components.
    
    Extends base monitoring with additional capabilities needed for ChatEventMonitor
    integration and comprehensive health auditing.
    
    Design Principles:
    - Monitor operates independently of observed components
    - Handles component failures gracefully
    - Provides cross-validation capabilities
    - Maintains audit history for analysis
    - Supports business impact assessment
    
    Business Value:
    - Enables comprehensive failure detection
    - Provides business impact assessment
    - Supports operational decision making
    - Protects chat system reliability
    """
    
    @abstractmethod
    async def register_component_for_monitoring(
        self, 
        component_id: str, 
        component: MonitorableComponent
    ) -> None:
        """
        Register a component for enhanced monitoring and auditing.
        
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
        
        Enhanced implementation should:
        - Store health change in audit history
        - Analyze health trends for early warning
        - Cross-validate health claims against external data
        - Trigger alerts for business-critical health changes
        
        Args:
            component_id: ID of component reporting health change
            health_data: Current health status data
        """
        pass
    
    @abstractmethod
    async def audit_component_health(self, component_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive health audit of a monitored component.
        
        Enhanced auditing capability that provides:
        - Internal health status validation
        - Cross-validation against external data sources
        - Integration health assessment
        - Business impact analysis
        - Historical trend analysis
        
        Args:
            component_id: ID of component to audit
            
        Returns:
            Dict containing comprehensive audit results including:
            - Component internal health status
            - External validation results
            - Integration health assessment
            - Business impact indicators
            - Recommended actions
        """
        pass
    
    async def remove_component_from_monitoring(self, component_id: str) -> None:
        """
        Remove a component from monitoring with cleanup.
        
        Enhanced implementation with comprehensive cleanup and audit trail.
        
        Args:
            component_id: ID of component to stop monitoring
        """
        # Default implementation - monitors may override
        pass


class MonitoringIntegrationMixin:
    """
    Mixin class providing common monitoring integration functionality.
    
    Provides reusable implementation of monitoring integration patterns
    that components can include to reduce boilerplate code.
    
    Business Value: Accelerates monitoring integration across components
    while maintaining consistency and reducing implementation errors.
    """
    
    def __init__(self):
        """Initialize monitoring integration capabilities."""
        if not hasattr(self, '_monitor_observers'):
            self._monitor_observers = []
        if not hasattr(self, '_component_id'):
            self._component_id = self.__class__.__name__.lower()
    
    async def initialize_monitoring_integration(
        self, 
        component_id: Optional[str] = None,
        auto_register: bool = True
    ) -> None:
        """
        Initialize monitoring integration with optional auto-registration.
        
        Args:
            component_id: Custom component ID (defaults to class name)
            auto_register: Whether to auto-register with global monitors
        """
        if component_id:
            self._component_id = component_id
            
        if auto_register:
            await self._auto_register_with_monitors()
    
    async def _auto_register_with_monitors(self) -> None:
        """Automatically register with available system monitors."""
        try:
            # Try to register with ChatEventMonitor if available
            from netra_backend.app.websocket_core.event_monitor import chat_event_monitor
            
            if hasattr(chat_event_monitor, 'register_component_for_monitoring'):
                await chat_event_monitor.register_component_for_monitoring(
                    self._component_id, 
                    self
                )
                logger.info(f"Auto-registered {self._component_id} with ChatEventMonitor")
                
        except Exception as e:
            logger.warning(
                f"Auto-registration with monitors failed for {self._component_id}: {e}. "
                f"Component will operate without monitoring integration."
            )
    
    def get_component_id(self) -> str:
        """Get the component ID for monitoring purposes."""
        return getattr(self, '_component_id', self.__class__.__name__.lower())


# Export compatibility aliases for existing code
ComponentMonitor = EnhancedComponentMonitor

# Re-export from shared interfaces for compatibility
try:
    from shared.monitoring.interfaces import HealthStatus, MonitoringMetrics
except ImportError:
    logger.warning("Could not import HealthStatus and MonitoringMetrics from shared interfaces")
    
    # Provide minimal fallback implementations
    class HealthStatus:
        def __init__(self, healthy: bool, state: str, **kwargs):
            self.healthy = healthy
            self.state = state
            self.timestamp = time.time()
            for key, value in kwargs.items():
                setattr(self, key, value)
                
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items()}
    
    class MonitoringMetrics:
        def __init__(self):
            self.counters = {}
            self.gauges = {}
            
        def to_dict(self):
            return {"counters": self.counters, "gauges": self.gauges}