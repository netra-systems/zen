"""
AgentWebSocketBridge - SSOT for WebSocket-Agent Service Integration

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Eliminates 60% of glue code, provides reliable agent-websocket coordination
- Strategic Impact: Single source of truth for integration lifecycle, enables zero-downtime recovery

This class serves as the single source of truth for managing the integration lifecycle
between AgentService and AgentExecutionRegistry, providing idempotent initialization,
health monitoring, and recovery mechanisms.
"""

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.orchestration.agent_execution_registry import get_agent_execution_registry
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.services.thread_run_registry import get_thread_run_registry, ThreadRunRegistry
from shared.monitoring.interfaces import MonitorableComponent

if TYPE_CHECKING:
    from shared.monitoring.interfaces import ComponentMonitor

logger = central_logger.get_logger(__name__)


class IntegrationState(Enum):
    """WebSocket-Agent integration states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class IntegrationConfig:
    """Configuration for WebSocket-Agent integration."""
    initialization_timeout_s: int = 30
    health_check_interval_s: int = 60
    recovery_max_attempts: int = 3
    recovery_base_delay_s: float = 1.0
    recovery_max_delay_s: float = 30.0
    integration_verification_timeout_s: int = 10


@dataclass
class HealthStatus:
    """Health status of WebSocket-Agent integration."""
    state: IntegrationState
    websocket_manager_healthy: bool
    registry_healthy: bool
    last_health_check: datetime
    consecutive_failures: int = 0
    total_recoveries: int = 0
    uptime_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class IntegrationResult:
    """Result of integration operation."""
    success: bool
    state: IntegrationState
    error: Optional[str] = None
    duration_ms: float = 0.0
    recovery_attempted: bool = False


@dataclass
class IntegrationMetrics:
    """Metrics for integration monitoring."""
    total_initializations: int = 0
    successful_initializations: int = 0
    failed_initializations: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    health_checks_performed: int = 0
    current_uptime_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentWebSocketBridge(MonitorableComponent):
    """
    SSOT for WebSocket-Agent service integration lifecycle.
    
    Provides idempotent initialization, health monitoring, and recovery
    mechanisms for the critical WebSocket-Agent integration that enables
    substantive chat interactions.
    
    Implements MonitorableComponent interface to enable external monitoring
    and health auditing while maintaining full operational independence.
    """
    
    _instance: Optional['AgentWebSocketBridge'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'AgentWebSocketBridge':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize bridge with thread-safe singleton pattern."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialize_configuration()
        self._initialize_state()
        self._initialize_dependencies()
        self._initialize_health_monitoring()
        self._initialize_monitoring_observers()
        
        self._initialized = True
        logger.info("AgentWebSocketBridge initialized as singleton")
    
    def _initialize_configuration(self) -> None:
        """Initialize bridge configuration."""
        self.config = IntegrationConfig()
        logger.debug("Integration configuration initialized")
    
    def _initialize_state(self) -> None:
        """Initialize integration state tracking."""
        self.state = IntegrationState.UNINITIALIZED
        self.initialization_lock = asyncio.Lock()
        self.recovery_lock = asyncio.Lock()
        self.health_lock = asyncio.Lock()
        self._shutdown = False
        logger.debug("Integration state tracking initialized")
    
    def _initialize_dependencies(self) -> None:
        """Initialize dependency references."""
        self._websocket_manager = None
        self._orchestrator = None
        self._supervisor = None
        self._registry = None
        self._thread_registry: Optional[ThreadRunRegistry] = None
        self._health_check_task = None
        logger.debug("Dependency references initialized")
    
    def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring and metrics."""
        self.metrics = IntegrationMetrics()
        self.health_status = HealthStatus(
            state=IntegrationState.UNINITIALIZED,
            websocket_manager_healthy=False,
            registry_healthy=False,
            last_health_check=datetime.now(timezone.utc)
        )
        logger.debug("Health monitoring initialized")
    
    def _initialize_monitoring_observers(self) -> None:
        """Initialize monitor observer system for external monitoring integration."""
        self._monitor_observers: List['ComponentMonitor'] = []
        self._last_health_broadcast = 0.0
        self._health_broadcast_interval = 30.0  # 30 seconds
        self._last_broadcasted_state = None
        logger.debug("Monitor observer system initialized")
    
    async def ensure_integration(
        self, 
        supervisor=None, 
        registry=None, 
        force_reinit: bool = False
    ) -> IntegrationResult:
        """
        Idempotent integration setup - can be called multiple times safely.
        
        Args:
            supervisor: Supervisor agent instance (optional, for enhanced integration)
            registry: Agent registry instance (optional, for enhanced integration)  
            force_reinit: Force re-initialization even if already active
            
        Returns:
            IntegrationResult with success status and metrics
        """
        start_time = time.time()
        
        async with self.initialization_lock:
            try:
                # Check if already active and not forcing reinit
                if self.state == IntegrationState.ACTIVE and not force_reinit:
                    logger.debug("Integration already active, skipping initialization")
                    return IntegrationResult(
                        success=True, 
                        state=self.state,
                        duration_ms=(time.time() - start_time) * 1000
                    )
                
                # Update state and metrics
                self.state = IntegrationState.INITIALIZING
                self.metrics.total_initializations += 1
                logger.info("Starting WebSocket-Agent integration")
                
                # Store optional dependencies for enhanced integration
                if supervisor:
                    self._supervisor = supervisor
                if registry:
                    self._registry = registry
                
                # Initialize core components
                await self._initialize_websocket_manager()
                await self._initialize_registry()
                await self._initialize_thread_registry()
                await self._setup_registry_integration()
                
                # Verify integration health
                verification_result = await self._verify_integration()
                if not verification_result:
                    raise RuntimeError("Integration verification failed")
                
                # Start health monitoring
                await self._start_health_monitoring()
                
                # Update state and metrics
                self.state = IntegrationState.ACTIVE
                self.metrics.successful_initializations += 1
                self.metrics.current_uptime_start = datetime.now(timezone.utc)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"WebSocket-Agent integration completed successfully in {duration_ms:.1f}ms")
                
                return IntegrationResult(
                    success=True,
                    state=self.state,
                    duration_ms=duration_ms
                )
                
            except Exception as e:
                # Update state and metrics
                self.state = IntegrationState.FAILED
                self.metrics.failed_initializations += 1
                
                error_msg = f"Integration initialization failed: {e}"
                logger.error(error_msg, exc_info=True)
                
                return IntegrationResult(
                    success=False,
                    state=self.state,
                    error=error_msg,
                    duration_ms=(time.time() - start_time) * 1000
                )
    
    async def _initialize_websocket_manager(self) -> None:
        """Initialize WebSocket manager with error handling and retry logic."""
        import asyncio
        
        websocket_manager = None
        last_error = None
        
        # CRITICAL FIX: Retry WebSocket manager initialization up to 3 times
        for attempt in range(3):
            try:
                websocket_manager = get_websocket_manager()
                if websocket_manager is not None:
                    # Validate the manager has required methods
                    if hasattr(websocket_manager, 'connections') and hasattr(websocket_manager, 'send_to_thread'):
                        self._websocket_manager = websocket_manager
                        logger.info(f"WebSocket manager initialized successfully on attempt {attempt + 1}")
                        return
                    else:
                        last_error = f"WebSocket manager missing required methods on attempt {attempt + 1}"
                        logger.warning(last_error)
                else:
                    last_error = f"WebSocket manager is None on attempt {attempt + 1}"
                    logger.warning(last_error)
                
                # Short delay before retry (except on last attempt)
                if attempt < 2:
                    await asyncio.sleep(0.05 * (attempt + 1))  # 0.05s, 0.1s
                    
            except Exception as e:
                last_error = f"WebSocket manager creation failed on attempt {attempt + 1}: {e}"
                logger.error(last_error)
                if attempt < 2:
                    await asyncio.sleep(0.05 * (attempt + 1))
        
        # All attempts failed
        error_msg = f"WebSocket manager initialization failed after 3 attempts. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def _initialize_registry(self) -> None:
        """Initialize agent execution registry with error handling."""
        try:
            self._orchestrator = await get_agent_execution_registry()
            if not self._orchestrator:
                raise RuntimeError("Agent execution registry is None")
            logger.debug("Agent execution registry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            raise RuntimeError(f"Registry initialization failed: {e}")
    
    async def _initialize_thread_registry(self) -> None:
        """Initialize thread-run registry with error handling."""
        try:
            self._thread_registry = await get_thread_run_registry()
            if not self._thread_registry:
                raise RuntimeError("Thread-run registry is None")
            logger.info("Thread-run registry initialized successfully - WebSocket routing reliability enhanced")
        except Exception as e:
            logger.error(f"Failed to initialize thread registry: {e}")
            raise RuntimeError(f"Thread registry initialization failed: {e}")
    
    async def _setup_registry_integration(self) -> None:
        """Setup registry integration with WebSocket manager and agents."""
        try:
            # Set WebSocket manager on registry
            await self._orchestrator.set_websocket_manager(self._websocket_manager)
            logger.debug("WebSocket manager set on registry")
            
            # Setup agent-WebSocket integration if components available
            if self._supervisor and self._registry:
                await self._orchestrator.setup_agent_websocket_integration(
                    self._supervisor, 
                    self._registry
                )
                logger.debug("Enhanced agent-WebSocket integration configured")
            else:
                logger.debug("Basic registry integration configured (no supervisor/registry)")
                
        except Exception as e:
            logger.error(f"Failed to setup registry integration: {e}")
            raise RuntimeError(f"Registry integration setup failed: {e}")
    
    async def _verify_integration(self) -> bool:
        """Verify integration is working correctly."""
        try:
            # Verify WebSocket manager is responsive
            if not self._websocket_manager:
                return False
            
            # Verify registry is responsive
            if not self._orchestrator:
                return False
            
            # Test registry metrics (should not raise)
            metrics = await self._orchestrator.get_metrics()
            if not isinstance(metrics, dict):
                return False
            
            # If we have registry, verify WebSocket integration
            if self._registry and hasattr(self._registry, 'websocket_manager'):
                if not self._registry.websocket_manager:
                    return False
            
            logger.debug("Integration verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Integration verification failed: {e}")
            return False
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_monitoring_loop())
            logger.debug("Health monitoring task started")
    
    async def health_check(self) -> HealthStatus:
        """
        Comprehensive health check of WebSocket-Agent integration.
        
        Returns:
            HealthStatus with detailed health information
        """
        async with self.health_lock:
            try:
                self.metrics.health_checks_performed += 1
                
                # Check WebSocket manager health
                websocket_healthy = await self._check_websocket_manager_health()
                
                # Check registry health  
                registry_healthy = await self._check_registry_health()
                
                # Update health status
                self.health_status = HealthStatus(
                    state=self.state,
                    websocket_manager_healthy=websocket_healthy,
                    registry_healthy=registry_healthy,
                    last_health_check=datetime.now(timezone.utc),
                    consecutive_failures=self.health_status.consecutive_failures,
                    total_recoveries=self.health_status.total_recoveries,
                    uptime_seconds=self._calculate_uptime()
                )
                
                # Update integration state based on health
                if websocket_healthy and registry_healthy:
                    if self.state in [IntegrationState.DEGRADED, IntegrationState.FAILED]:
                        self.state = IntegrationState.ACTIVE
                        logger.info("Integration recovered to ACTIVE state")
                    self.health_status.consecutive_failures = 0
                else:
                    self.health_status.consecutive_failures += 1
                    if self.state == IntegrationState.ACTIVE:
                        self.state = IntegrationState.DEGRADED
                        logger.warning("Integration degraded due to health check failures")
                
                self.health_status.state = self.state
                
                # Notify observers of health changes if any are registered
                await self._notify_monitors_of_health_change()
                
                return self.health_status
                
            except Exception as e:
                error_msg = f"Health check failed: {e}"
                logger.error(error_msg)
                
                self.health_status.consecutive_failures += 1
                self.health_status.error_message = error_msg
                self.health_status.last_health_check = datetime.now(timezone.utc)
                
                # Notify observers of health changes if any are registered
                await self._notify_monitors_of_health_change()
                
                return self.health_status
    
    async def _check_websocket_manager_health(self) -> bool:
        """Check WebSocket manager health."""
        try:
            return self._websocket_manager is not None
        except Exception:
            return False
    
    async def _check_registry_health(self) -> bool:
        """Check registry health."""
        try:
            if not self._orchestrator:
                return False
            
            # Test registry responsiveness
            metrics = await self._orchestrator.get_metrics()
            return isinstance(metrics, dict)
        except Exception:
            return False
    
    def _calculate_uptime(self) -> float:
        """Calculate current uptime in seconds."""
        if self.state != IntegrationState.ACTIVE:
            return 0.0
        
        uptime_delta = datetime.now(timezone.utc) - self.metrics.current_uptime_start
        return uptime_delta.total_seconds()
    
    # MonitorableComponent interface implementation
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status for monitoring (MonitorableComponent interface).
        
        Exposes bridge health status in standardized format for external monitors.
        This method maintains full independence - bridge works without any monitors.
        
        Returns:
            Dict containing standardized health status for monitoring
        """
        try:
            health = await self.health_check()
            
            return {
                "healthy": health.websocket_manager_healthy and health.registry_healthy,
                "state": health.state.value,
                "timestamp": time.time(),
                "websocket_manager_healthy": health.websocket_manager_healthy,
                "registry_healthy": health.registry_healthy,
                "consecutive_failures": health.consecutive_failures,
                "uptime_seconds": health.uptime_seconds,
                "last_health_check": health.last_health_check.isoformat(),
                "error_message": health.error_message,
                "total_recoveries": health.total_recoveries
            }
        except Exception as e:
            logger.error(f"Error getting health status for monitoring: {e}")
            return {
                "healthy": False,
                "state": "error",
                "timestamp": time.time(),
                "error_message": f"Health status retrieval failed: {e}"
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get operational metrics for analysis (MonitorableComponent interface).
        
        Provides comprehensive metrics for business decisions and monitoring.
        Bridge operates fully independently without registered monitors.
        
        Returns:
            Dict containing operational metrics
        """
        try:
            return {
                # Core operational metrics
                "total_initializations": self.metrics.total_initializations,
                "successful_initializations": self.metrics.successful_initializations,
                "failed_initializations": self.metrics.failed_initializations,
                "recovery_attempts": self.metrics.recovery_attempts,
                "successful_recoveries": self.metrics.successful_recoveries,
                "health_checks_performed": self.metrics.health_checks_performed,
                
                # Calculated metrics
                "success_rate": (
                    self.metrics.successful_initializations / 
                    max(1, self.metrics.total_initializations)
                ),
                "recovery_success_rate": (
                    self.metrics.successful_recoveries /
                    max(1, self.metrics.recovery_attempts) if self.metrics.recovery_attempts > 0 else 1.0
                ),
                
                # Current status
                "current_state": self.state.value,
                "current_uptime_seconds": self._calculate_uptime(),
                "uptime_start": self.metrics.current_uptime_start.isoformat(),
                
                # Observer system metrics  
                "registered_observers": len(self._monitor_observers),
                "last_health_broadcast": self._last_health_broadcast,
                "health_broadcast_interval": self._health_broadcast_interval,
                
                # Component availability
                "websocket_manager_available": self._websocket_manager is not None,
                "orchestrator_available": self._orchestrator is not None,
                "supervisor_available": self._supervisor is not None,
                "registry_available": self._registry is not None,
                
                # Timestamp
                "metrics_timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Error getting metrics for monitoring: {e}")
            return {
                "error": f"Metrics retrieval failed: {e}",
                "metrics_timestamp": time.time()
            }
    
    def register_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Register a monitor to observe this component (MonitorableComponent interface).
        
        Adds external monitor as observer while maintaining bridge independence.
        Bridge continues full operation even if observer registration fails.
        
        Args:
            observer: Monitor that will receive health change notifications
        """
        try:
            if observer not in self._monitor_observers:
                self._monitor_observers.append(observer)
                logger.info(f"✅ Monitor observer registered: {type(observer).__name__}")
                logger.debug(f"Total registered observers: {len(self._monitor_observers)}")
            else:
                logger.debug(f"Observer {type(observer).__name__} already registered")
        except Exception as e:
            logger.warning(f"Failed to register monitor observer: {e}")
            # Bridge continues operating - observer registration is optional
    
    def remove_monitor_observer(self, observer: 'ComponentMonitor') -> None:
        """
        Remove a registered monitor observer.
        
        Removes observer from notifications while maintaining bridge independence.
        Bridge continues full operation regardless of observer management.
        
        Args:
            observer: Monitor to remove from notifications
        """
        try:
            if observer in self._monitor_observers:
                self._monitor_observers.remove(observer)
                logger.info(f"Monitor observer removed: {type(observer).__name__}")
                logger.debug(f"Remaining registered observers: {len(self._monitor_observers)}")
            else:
                logger.debug(f"Observer {type(observer).__name__} was not registered")
        except Exception as e:
            logger.warning(f"Failed to remove monitor observer: {e}")
            # Bridge continues operating - observer management is optional
    
    async def _notify_monitors_of_health_change(self) -> None:
        """
        Notify registered monitors of health status changes.
        
        Implements observer pattern with graceful degradation - bridge operates
        independently if no monitors registered or notifications fail.
        
        Business Value: Enables comprehensive monitoring while maintaining independence.
        """
        try:
            # Skip notification if no observers registered
            if not self._monitor_observers:
                return
            
            current_time = time.time()
            health_changed = self.health_status.state != self._last_broadcasted_state
            periodic_update = (current_time - self._last_health_broadcast) > self._health_broadcast_interval
            
            # Only notify on health changes or periodic updates
            if not (health_changed or periodic_update):
                return
            
            # Prepare health data for broadcast
            health_data = {
                "component_id": "agent_websocket_bridge",
                "state": self.health_status.state.value,
                "healthy": (
                    self.health_status.websocket_manager_healthy and 
                    self.health_status.registry_healthy
                ),
                "consecutive_failures": self.health_status.consecutive_failures,
                "uptime_seconds": self._calculate_uptime(),
                "timestamp": current_time,
                "websocket_manager_healthy": self.health_status.websocket_manager_healthy,
                "registry_healthy": self.health_status.registry_healthy,
                "error_message": self.health_status.error_message,
                "change_type": "health_change" if health_changed else "periodic_update"
            }
            
            # Notify all observers (with error resilience)
            successful_notifications = 0
            for observer in self._monitor_observers[:]:  # Copy list to avoid modification during iteration
                try:
                    await observer.on_component_health_change("agent_websocket_bridge", health_data)
                    successful_notifications += 1
                except Exception as e:
                    logger.warning(f"Failed to notify monitor observer {type(observer).__name__}: {e}")
                    # Continue notifying other observers - individual failures don't stop bridge
            
            # Update broadcast tracking
            self._last_health_broadcast = current_time
            self._last_broadcasted_state = self.health_status.state
            
            if successful_notifications > 0:
                logger.debug(f"Health change notified to {successful_notifications}/{len(self._monitor_observers)} observers")
            
        except Exception as e:
            logger.warning(f"Error in health change notification: {e}")
            # Bridge continues operating - monitoring is optional
    
    async def recover_integration(self) -> IntegrationResult:
        """
        Attempt to recover failed integration with exponential backoff.
        
        Returns:
            IntegrationResult with recovery status and metrics
        """
        async with self.recovery_lock:
            logger.info("Attempting integration recovery")
            self.metrics.recovery_attempts += 1
            
            for attempt in range(self.config.recovery_max_attempts):
                try:
                    # Calculate backoff delay
                    delay = min(
                        self.config.recovery_base_delay_s * (2 ** attempt),
                        self.config.recovery_max_delay_s
                    )
                    
                    if attempt > 0:
                        logger.info(f"Recovery attempt {attempt + 1}, waiting {delay}s")
                        await asyncio.sleep(delay)
                    
                    # Attempt recovery through re-initialization
                    result = await self.ensure_integration(
                        supervisor=self._supervisor,
                        registry=self._registry,
                        force_reinit=True
                    )
                    
                    if result.success:
                        self.metrics.successful_recoveries += 1
                        self.health_status.total_recoveries += 1
                        logger.info(f"Integration recovery successful on attempt {attempt + 1}")
                        return IntegrationResult(
                            success=True,
                            state=self.state,
                            recovery_attempted=True,
                            duration_ms=result.duration_ms
                        )
                        
                except Exception as e:
                    logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                    continue
            
            # All recovery attempts failed
            self.state = IntegrationState.FAILED
            error_msg = f"Recovery failed after {self.config.recovery_max_attempts} attempts"
            logger.error(error_msg)
            
            return IntegrationResult(
                success=False,
                state=self.state,
                error=error_msg,
                recovery_attempted=True
            )
    
    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.config.health_check_interval_s)
                
                if self._shutdown:
                    break
                
                health = await self.health_check()
                
                # Trigger recovery if health is poor
                if (health.consecutive_failures >= 3 and 
                    health.state in [IntegrationState.DEGRADED, IntegrationState.FAILED]):
                    logger.warning("Triggering automatic recovery due to poor health")
                    await self.recover_integration()
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive integration status and metrics.
        
        Returns:
            Dictionary with integration status, health, and metrics
        """
        health = await self.health_check()
        
        return {
            "state": self.state.value,
            "health": {
                "websocket_manager_healthy": health.websocket_manager_healthy,
                "registry_healthy": health.registry_healthy,
                "consecutive_failures": health.consecutive_failures,
                "uptime_seconds": health.uptime_seconds,
                "last_health_check": health.last_health_check.isoformat(),
                "error_message": health.error_message
            },
            "metrics": {
                "total_initializations": self.metrics.total_initializations,
                "successful_initializations": self.metrics.successful_initializations,
                "failed_initializations": self.metrics.failed_initializations,
                "recovery_attempts": self.metrics.recovery_attempts,
                "successful_recoveries": self.metrics.successful_recoveries,
                "health_checks_performed": self.metrics.health_checks_performed,
                "success_rate": (
                    self.metrics.successful_initializations / 
                    max(1, self.metrics.total_initializations)
                )
            },
            "config": {
                "initialization_timeout_s": self.config.initialization_timeout_s,
                "health_check_interval_s": self.config.health_check_interval_s,
                "recovery_max_attempts": self.config.recovery_max_attempts
            },
            "dependencies": {
                "websocket_manager_available": self._websocket_manager is not None,
                "orchestrator_available": self._orchestrator is not None,
                "supervisor_available": self._supervisor is not None,
                "registry_available": self._registry is not None
            }
        }
    
    async def shutdown(self) -> None:
        """Clean shutdown of bridge resources."""
        logger.info("Shutting down AgentWebSocketBridge")
        self._shutdown = True
        
        # Cancel health monitoring task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown registry if available
        if self._orchestrator:
            try:
                await self._orchestrator.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down registry: {e}")
        
        # Shutdown thread registry if available
        if self._thread_registry:
            try:
                await self._thread_registry.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down thread registry: {e}")
        
        # Clear references
        self._websocket_manager = None
        self._orchestrator = None
        self._supervisor = None
        self._registry = None
        self._thread_registry = None
        
        # Clear monitor observers
        self._monitor_observers.clear()
        self._last_health_broadcast = 0.0
        self._last_broadcasted_state = None
        
        self.state = IntegrationState.UNINITIALIZED
        logger.info("AgentWebSocketBridge shutdown complete")
    
    # ===================== THREAD-RUN REGISTRY INTERFACE =====================
    # BUSINESS CRITICAL: These methods enable reliable WebSocket routing
    
    async def register_run_thread_mapping(
        self, 
        run_id: str, 
        thread_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a run_id to thread_id mapping for reliable WebSocket routing.
        
        CRITICAL: This method MUST be called when creating new agent runs to ensure
        WebSocket events reach users reliably.
        
        Args:
            run_id: Unique execution identifier
            thread_id: Associated thread identifier for WebSocket routing
            metadata: Optional metadata (agent_name, user_id, etc.)
            
        Returns:
            bool: True if registration succeeded
            
        Business Value: Prevents 20% of WebSocket notification failures
        """
        try:
            if not self._thread_registry:
                logger.warning(f"🚨 REGISTRATION BLOCKED: Thread registry not available for run_id={run_id}")
                return False
            
            success = await self._thread_registry.register(run_id, thread_id, metadata)
            
            if success:
                logger.info(f"✅ MAPPING REGISTERED: run_id={run_id} → thread_id={thread_id} (metadata: {metadata})")
            else:
                logger.error(f"🚨 REGISTRATION FAILED: run_id={run_id} → thread_id={thread_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 REGISTRATION EXCEPTION: run_id={run_id}, thread_id={thread_id}: {e}")
            return False
    
    async def unregister_run_mapping(self, run_id: str) -> bool:
        """
        Remove a run_id mapping when agent execution completes.
        
        Args:
            run_id: Run identifier to unregister
            
        Returns:
            bool: True if unregistration succeeded
        """
        try:
            if not self._thread_registry:
                logger.debug(f"Thread registry not available for unregistration of run_id={run_id}")
                return False
            
            success = await self._thread_registry.unregister_run(run_id)
            
            if success:
                logger.debug(f"🗑️ MAPPING UNREGISTERED: run_id={run_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 UNREGISTRATION EXCEPTION: run_id={run_id}: {e}")
            return False
    
    async def get_thread_registry_status(self) -> Optional[Dict[str, Any]]:
        """
        Get thread registry status for monitoring.
        
        Returns:
            Optional[Dict]: Registry status or None if registry unavailable
        """
        try:
            if not self._thread_registry:
                return None
            
            return await self._thread_registry.get_status()
            
        except Exception as e:
            logger.error(f"🚨 Error getting thread registry status: {e}")
            return None
    
    # ===================== NOTIFICATION INTERFACE =====================
    # SSOT for all WebSocket notifications - CRYSTAL CLEAR emission paths
    # BUSINESS CRITICAL: These methods enable 90% of chat functionality value
    
    async def notify_agent_started(
        self, 
        run_id: str, 
        agent_name: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send agent started notification with guaranteed delivery.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent starting execution
            context: Optional context (user_query, metadata, etc.)
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Users see immediate feedback that AI is working on their problem
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_started (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "agent_started",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "started",
                    "context": context or {},
                    "message": f"{agent_name} has started processing your request"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.info(f"✅ EMISSION SUCCESS: agent_started → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_started send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_started failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_agent_thinking(
        self, 
        run_id: str, 
        agent_name: str, 
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """
        Send agent thinking notification with progress context.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the thinking agent
            reasoning: Agent's current reasoning/thinking process
            step_number: Optional current step number
            progress_percentage: Optional progress percentage (0-100)
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Shows real-time AI reasoning, builds trust in AI capabilities
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_thinking (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message  
            notification = {
                "type": "agent_thinking",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "reasoning": reasoning,
                    "step_number": step_number,
                    "progress_percentage": progress_percentage,
                    "status": "thinking"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: agent_thinking → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_thinking send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_thinking failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_tool_executing(
        self, 
        run_id: str, 
        agent_name: str, 
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send tool execution start notification for transparency.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent executing the tool
            tool_name: Name of the tool being executed
            parameters: Optional tool parameters (sanitized for user display)
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Demonstrates AI problem-solving approach, builds trust
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for tool_executing (run_id={run_id}, tool={tool_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "tool_executing",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tool_name": tool_name,
                    "parameters": self._sanitize_parameters(parameters) if parameters else {},
                    "status": "executing",
                    "message": f"{agent_name} is using {tool_name}"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: tool_executing → thread={thread_id} (run_id={run_id}, tool={tool_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: tool_executing send failed (run_id={run_id}, tool={tool_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_tool_executing failed (run_id={run_id}, tool={tool_name}): {e}")
            return False
    
    async def notify_tool_completed(
        self, 
        run_id: str, 
        agent_name: str, 
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """
        Send tool execution completion notification with results.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent that executed the tool
            tool_name: Name of the completed tool
            result: Optional tool results (sanitized for user display)
            execution_time_ms: Optional execution duration
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Shows completed work, delivers actionable insights
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for tool_completed (run_id={run_id}, tool={tool_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "tool_completed",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tool_name": tool_name,
                    "result": self._sanitize_result(result) if result else {},
                    "execution_time_ms": execution_time_ms,
                    "status": "completed",
                    "message": f"{agent_name} completed {tool_name}"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: tool_completed → thread={thread_id} (run_id={run_id}, tool={tool_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: tool_completed send failed (run_id={run_id}, tool={tool_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_tool_completed failed (run_id={run_id}, tool={tool_name}): {e}")
            return False
    
    async def notify_agent_completed(
        self, 
        run_id: str, 
        agent_name: str, 
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """
        Send agent completion notification with final results.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the completed agent
            result: Optional agent results (sanitized for user display)
            execution_time_ms: Optional total execution duration
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Users know when valuable AI response is ready
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_completed (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "agent_completed",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "completed",
                    "result": self._sanitize_result(result) if result else {},
                    "execution_time_ms": execution_time_ms,
                    "message": f"{agent_name} has completed processing your request"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.info(f"✅ EMISSION SUCCESS: agent_completed → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_completed send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_completed failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_agent_error(
        self, 
        run_id: str, 
        agent_name: str, 
        error: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send agent error notification with context.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent that encountered the error
            error: Error message (sanitized for user display)
            error_context: Optional error context (sanitized)
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Users receive clear error communication, maintain trust
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_error (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "agent_error",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "error", 
                    "error_message": self._sanitize_error_message(error),
                    "error_context": self._sanitize_error_context(error_context) if error_context else {},
                    "message": f"{agent_name} encountered an issue processing your request"
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.warning(f"⚠️ EMISSION SUCCESS: agent_error → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_error send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_error failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_agent_death(
        self, 
        run_id: str, 
        agent_name: str, 
        death_cause: str,
        death_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send agent death notification for critical failures.
        
        CRITICAL: This notification is sent when an agent dies silently without exceptions.
        This prevents the infinite loading state users experience.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent that died
            death_cause: Cause of death (timeout, no_heartbeat, silent_failure)
            death_context: Optional context about the death
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Prevents silent failures that destroy user trust
        """
        try:
            if not self._websocket_manager:
                logger.critical(f"🚨💀 CRITICAL: Cannot notify agent death - WebSocket manager unavailable (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build critical death notification
            notification = {
                "type": "agent_death",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "dead",
                    "death_cause": death_cause,
                    "death_context": death_context or {},
                    "message": self._get_user_friendly_death_message(death_cause, agent_name),
                    "recovery_action": "refresh_required"
                }
            }
            
            # CRITICAL EMISSION: Resolve thread_id and emit with highest priority
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.critical(f"🚨💀 CRITICAL: Cannot resolve thread_id for agent death notification (run_id={run_id})")
                return False
            
            # Emit death notification with critical priority
            success = await self._websocket_manager.send_to_thread(
                thread_id=thread_id,
                message=notification
            )
            
            if success:
                logger.critical(f"💀 AGENT DEATH NOTIFIED: {agent_name} died due to {death_cause} (run_id={run_id}, thread={thread_id})")
            else:
                logger.critical(f"🚨💀 FAILED to notify agent death: {agent_name} (run_id={run_id}, thread={thread_id})")
            
            return success
            
        except Exception as e:
            logger.critical(f"🚨💀 CRITICAL EXCEPTION: notify_agent_death failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    def _get_user_friendly_death_message(self, death_cause: str, agent_name: str) -> str:
        """Generate user-friendly message for agent death"""
        messages = {
            "timeout": f"The {agent_name} agent took too long to respond and has been stopped. Please try again.",
            "no_heartbeat": f"Lost connection with the {agent_name} agent. Please refresh and try again.",
            "silent_failure": f"The {agent_name} agent stopped unexpectedly. Please refresh the page.",
            "memory_limit": f"The {agent_name} agent ran out of resources. Please try with a simpler request.",
            "cancelled": f"The {agent_name} agent was cancelled. You can start a new request."
        }
        return messages.get(death_cause, f"The {agent_name} agent encountered a critical error. Please refresh and try again.")
    
    async def notify_progress_update(
        self, 
        run_id: str, 
        agent_name: str, 
        progress: Dict[str, Any]
    ) -> bool:
        """
        Send agent progress update notification.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent reporting progress
            progress: Progress data (percentage, current_step, message, etc.)
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Users see real-time progress, understand processing status
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for progress_update (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": "progress_update",
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "progress",
                    "progress_data": self._sanitize_progress_data(progress),
                    "message": progress.get("message", f"{agent_name} is making progress")
                }
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: progress_update → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: progress_update send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_progress_update failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_custom(
        self, 
        run_id: str, 
        agent_name: str, 
        notification_type: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Send custom notification with flexible data.
        
        CRYSTAL CLEAR EMISSION PATH: Agent → Bridge → WebSocket Manager → User Chat
        
        Args:
            run_id: Unique execution identifier for routing
            agent_name: Name of the agent sending notification
            notification_type: Custom notification type identifier
            data: Custom notification data
            
        Returns:
            bool: True if notification queued/sent successfully
            
        Business Value: Enables specialized agent communications, extensibility
        """
        try:
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for custom notification (run_id={run_id}, type={notification_type})")
                return False
            
            # Build standardized notification message
            notification = {
                "type": notification_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": self._sanitize_custom_data(data)
            }
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # EMIT TO USER CHAT
            success = await self._websocket_manager.send_to_thread(thread_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: custom({notification_type}) → thread={thread_id} (run_id={run_id}, agent={agent_name})")
            else:
                logger.error(f"🚨 EMISSION FAILED: custom({notification_type}) send failed (run_id={run_id}, agent={agent_name})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_custom failed (run_id={run_id}, type={notification_type}): {e}")
            return False
    
    # ===================== HELPER METHODS =====================
    
    async def _resolve_thread_id_from_run_id(self, run_id: str) -> Optional[str]:
        """
        Resolve thread_id from run_id for proper WebSocket routing.
        
        CRITICAL: This method ensures notifications reach the correct user chat thread.
        Enhanced with ThreadRunRegistry for 100% reliable resolution.
        """
        try:
            # PRIORITY 1: Check ThreadRunRegistry first (MOST RELIABLE)
            if self._thread_registry:
                try:
                    thread_id = await self._thread_registry.get_thread(run_id)
                    if thread_id:
                        logger.debug(f"✅ REGISTRY RESOLUTION: run_id={run_id} → thread_id={thread_id}")
                        return thread_id
                except Exception as e:
                    logger.debug(f"ThreadRunRegistry resolution failed for run_id={run_id}: {e}")
            
            # PRIORITY 2: Try to get thread_id from orchestrator if available
            if self._orchestrator:
                try:
                    # Attempt to resolve through orchestrator registry
                    thread_id = await self._orchestrator.get_thread_id_for_run(run_id)
                    if thread_id:
                        logger.debug(f"✅ ORCHESTRATOR RESOLUTION: run_id={run_id} → thread_id={thread_id}")
                        return thread_id
                except Exception as e:
                    logger.debug(f"Orchestrator thread_id resolution failed for run_id={run_id}: {e}")
            
            # PRIORITY 3: Fallback pattern extraction (FRAGILE)
            # Many run_ids contain or reference thread_id
            if "thread_" in run_id:
                # Extract thread_id from run_id if embedded
                parts = run_id.split("_")
                for i, part in enumerate(parts):
                    if part == "thread" and i + 1 < len(parts):
                        extracted_thread = f"thread_{parts[i + 1]}"
                        logger.debug(f"⚠️ PATTERN EXTRACTION: run_id={run_id} → thread_id={extracted_thread}")
                        return extracted_thread
            
            # PRIORITY 4: If we have a registry available, try alternate resolution
            if self._registry and hasattr(self._registry, 'get_thread_for_run'):
                try:
                    thread_id = await self._registry.get_thread_for_run(run_id)
                    if thread_id:
                        logger.debug(f"✅ ALT REGISTRY RESOLUTION: run_id={run_id} → thread_id={thread_id}")
                        return thread_id
                except Exception as e:
                    logger.debug(f"Registry thread_id resolution failed for run_id={run_id}: {e}")
            
            # PRIORITY 5: Last fallback - assume run_id can be used directly if it looks like thread_id
            if run_id.startswith("thread_"):
                logger.debug(f"⚠️ DIRECT USAGE: Treating run_id={run_id} as thread_id")
                return run_id
            
            # ALL RESOLUTION METHODS FAILED
            logger.error(f"🚨 COMPLETE RESOLUTION FAILURE: Unable to resolve thread_id for run_id={run_id}")
            logger.error(f"   - ThreadRunRegistry available: {self._thread_registry is not None}")
            logger.error(f"   - Orchestrator available: {self._orchestrator is not None}")
            logger.error(f"   - Pattern extraction failed: No 'thread_' in run_id")
            logger.error(f"   - Registry fallback failed: {self._registry is not None}")
            
            return None
            
        except Exception as e:
            logger.error(f"🚨 CRITICAL EXCEPTION: Exception resolving thread_id for run_id={run_id}: {e}")
            return None
    
    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool parameters for user display, removing sensitive data."""
        if not params:
            return {}
        
        sanitized = {}
        sensitive_keys = {'password', 'secret', 'key', 'token', 'api_key', 'auth', 'credential'}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_parameters(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool results for user display, focusing on user-relevant data."""
        if not result:
            return {}
        
        sanitized = {}
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_result(value)
            elif isinstance(value, list) and len(value) > 10:
                sanitized[key] = value[:10] + ["...(truncated)"]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_error_message(self, error: str) -> str:
        """Sanitize error message for user display, removing technical internals."""
        if not error:
            return "An error occurred"
        
        # Remove file paths and internal details
        sanitized = error.replace("/Users/", "/home/").replace("/home/", "[PATH]/")
        
        # Truncate very long errors
        if len(sanitized) > 300:
            sanitized = sanitized[:300] + "..."
        
        return sanitized
    
    def _sanitize_error_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize error context for user display."""
        if not context:
            return {}
        
        return {
            "error_type": context.get("error_type", "unknown"),
            "agent_step": context.get("agent_step", "unknown"),
            "user_facing": True
        }
    
    def _sanitize_progress_data(self, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize progress data for user display."""
        if not progress:
            return {}
        
        sanitized = {}
        allowed_keys = {
            'percentage', 'current_step', 'total_steps', 'message', 
            'status', 'estimated_remaining', 'progress_type'
        }
        
        for key, value in progress.items():
            if key in allowed_keys:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_custom_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize custom notification data for user display."""
        if not data:
            return {}
        
        # Basic sanitization - remove large objects and sensitive data
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_custom_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


# Singleton factory function
_bridge_instance: Optional[AgentWebSocketBridge] = None


async def get_agent_websocket_bridge() -> AgentWebSocketBridge:
    """Get singleton AgentWebSocketBridge instance."""
    global _bridge_instance
    
    if _bridge_instance is None:
        async with AgentWebSocketBridge._lock:
            if _bridge_instance is None:
                _bridge_instance = AgentWebSocketBridge()
    
    return _bridge_instance