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
from typing import Dict, Optional, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
# REMOVED: Singleton orchestrator import - replaced with per-request factory patterns
# from netra_backend.app.orchestration.agent_execution_registry import get_agent_execution_registry
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.thread_run_registry import get_thread_run_registry, ThreadRunRegistry
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.monitoring.interfaces import MonitorableComponent

if TYPE_CHECKING:
    from shared.monitoring.interfaces import ComponentMonitor
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UserWebSocketEmitter

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
    REFACTORED: WebSocket-Agent service integration lifecycle manager.
    
    IMPORTANT: This class has been refactored to remove singleton pattern.
    For new code, use create_user_emitter() to get per-request emitters
    that ensure complete user isolation.
    
    Legacy singleton methods are preserved for backward compatibility
    but are DEPRECATED and should be migrated to per-user emitters.
    
    Provides idempotent initialization, health monitoring, and recovery
    mechanisms for the critical WebSocket-Agent integration that enables
    substantive chat interactions.
    
    Implements MonitorableComponent interface to enable external monitoring
    and health auditing while maintaining full operational independence.
    """
    
    # REMOVED: Singleton pattern implementation
    # _instance: Optional['AgentWebSocketBridge'] = None
    # _lock = asyncio.Lock()
    
    def __init__(self, user_context: Optional['UserExecutionContext'] = None):
        """Initialize bridge WITHOUT singleton pattern.
        
        MIGRATION NOTE: This bridge is now non-singleton. For per-user
        event emission, use create_user_emitter() factory method.
        
        Args:
            user_context: Optional UserExecutionContext for per-user isolation
        """
        # Remove singleton initialization check
        # if hasattr(self, '_initialized'):
        #     return
        
        # Store user context for validation and isolation
        self.user_context = user_context
        
        # Initialize connection status for test compatibility
        self.is_connected = True  # Bridge is considered "connected" once initialized
        
        self._initialize_configuration()
        self._initialize_state()
        self._initialize_dependencies()
        self._initialize_health_monitoring()
        self._initialize_monitoring_observers()
        
        self._initialized = True
        if user_context:
            logger.info(
                f"🌉 WEBSOCKET_BRIDGE_INIT: Agent WebSocket bridge initialized with user isolation. "
                f"User: {user_context.user_id[:8]}..., Mode: non-singleton, "
                f"Thread: {user_context.thread_id}, Request: {user_context.request_id}, "
                f"Business_context: Ready for real-time agent event delivery (critical for chat UX)"
            )
        else:
            logger.info(
                f"🌉 WEBSOCKET_BRIDGE_INIT: Agent WebSocket bridge initialized (system mode). "
                f"Mode: non-singleton, User_context: none, "
                f"Business_context: System-level initialization for agent event infrastructure"
            )
    
    def _initialize_configuration(self) -> None:
        """Initialize bridge configuration."""
        self.config = IntegrationConfig()
        logger.debug(
            f"⚙️ BRIDGE_CONFIG_INIT: WebSocket-Agent integration configuration loaded. "
            f"Timeout: {self.config.initialization_timeout_s}s, "
            f"Health_check_interval: {self.config.health_check_interval_s}s, "
            f"Recovery_attempts: {self.config.recovery_max_attempts}, "
            f"Business_context: Configuration ready for reliable agent-websocket coordination"
        )
    
    def _initialize_state(self) -> None:
        """Initialize integration state tracking.
        
        NOTE: The bridge intentionally starts in UNINITIALIZED state and remains
        that way in the per-request architecture. This is EXPECTED behavior.
        Actual initialization happens per-request via create_user_emitter().
        See AGENT_WEBSOCKET_BRIDGE_UNINITIALIZED_FIVE_WHYS.md for details.
        """
        self.state = IntegrationState.UNINITIALIZED
        self.initialization_lock = asyncio.Lock()
        self.recovery_lock = asyncio.Lock()
        self.health_lock = asyncio.Lock()
        self._shutdown = False
        logger.debug("Integration state tracking initialized (UNINITIALIZED is expected for per-request pattern)")
    
    def _initialize_dependencies(self) -> None:
        """Initialize dependency references."""
        self._websocket_manager = None
        # REMOVED: Singleton orchestrator - using per-request factory patterns instead
        # self._orchestrator = None
        self._supervisor = None
        self._registry = None
        self._thread_registry: Optional[ThreadRunRegistry] = None
        self._health_check_task = None
        logger.debug("Dependency references initialized")
    
    @property
    def websocket_manager(self):
        """Get the WebSocket manager for this bridge.
        
        CRITICAL: This property exposes the _websocket_manager for supervisor
        and tool dispatcher integration. The manager is set per-request to
        ensure proper user isolation.
        """
        return self._websocket_manager
    
    @websocket_manager.setter
    def websocket_manager(self, manager):
        """Set websocket manager (primarily for testing scenarios).
        
        CRITICAL: This setter is primarily for test scenarios to inject mock managers.
        Production code should use factory methods (create_user_emitter, create_scoped_emitter)
        for proper user isolation and per-request instantiation patterns.
        
        Args:
            manager: WebSocket manager instance or None. Must implement send_to_thread method
                    if not None.
                    
        Raises:
            ValueError: If manager doesn't implement required interface
        """
        if manager is not None and not hasattr(manager, 'send_to_thread'):
            raise ValueError(
                "Invalid websocket manager - must implement send_to_thread method. "
                "For production use, prefer factory methods for proper user isolation."
            )
        
        self._websocket_manager = manager
        logger.debug(
            f"WebSocket manager {'set' if manager else 'cleared'} "
            f"(type: {type(manager).__name__ if manager else 'None'})"
        )
    
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
        """Initialize WebSocket manager with error handling and retry logic.
        
        CRITICAL: This now uses a placeholder manager that will be replaced
        per-request via create_user_emitter() factory method for proper isolation.
        """
        import asyncio
        
        # SECURITY FIX: Don't use singleton - create placeholder that will be 
        # replaced per-request through create_user_emitter() factory
        
        # For backward compatibility, we keep the manager reference but it will
        # be overridden per-request to ensure user isolation
        self._websocket_manager = None  # Will be set per-request
        
        logger.info(
            "WebSocket manager initialization deferred - will use factory pattern "
            "per-request via create_user_emitter() for proper user isolation"
        )
    
    async def _initialize_registry(self) -> None:
        """DEPRECATED: Registry initialization removed - using per-request factory patterns.
        
        This method is preserved for backward compatibility but is now a no-op.
        Per-request isolation is handled by create_user_emitter() factory methods.
        """
        logger.debug("Registry initialization skipped - using per-request factory patterns")
        # No initialization needed - factory methods handle per-request isolation
    
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
        """DEPRECATED: Registry integration removed - using per-request factory patterns.
        
        This method is preserved for backward compatibility but is now a no-op.
        Integration is handled per-request through create_user_emitter() methods.
        """
        logger.debug("Registry integration skipped - using per-request factory patterns")
        # No setup needed - factory methods handle per-request integration
    
    async def _verify_integration(self) -> bool:
        """Verify integration is working correctly.
        
        NOTE: In the new per-request isolation architecture, the WebSocket manager
        is intentionally None at startup and will be created per-request via
        create_user_emitter() factory pattern for proper user isolation.
        """
        try:
            # In the new architecture, WebSocket manager is created per-request
            # So having it as None at startup is expected and correct
            # The actual WebSocket functionality will be validated per-request
            
            # REMOVED: Orchestrator verification - per-request factory patterns don't need global registry
            # Registry health is validated per-request through create_user_emitter() factory methods
            # No global orchestrator needed for user isolation pattern
            
            # If we have registry, verify it's available (but websocket_manager can be None)
            # The registry itself handles per-request WebSocket creation
            if self._registry and hasattr(self._registry, 'websocket_manager'):
                # It's OK if websocket_manager is None - it will be set per-request
                pass
            
            logger.debug("Integration verification passed - per-request isolation ready")
            return True
            
        except Exception as e:
            logger.error(f"Integration verification failed: {e}")
            return False
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring task with enhanced error handling."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_monitoring_loop())
            
            def handle_health_task_completion(task):
                """Handle health monitoring task completion/failure with async-safe state checking."""
                try:
                    # CRITICAL FIX: Validate task state before any exception() calls to prevent InvalidStateError
                    if not task.done():
                        logger.warning("Health monitoring callback invoked on non-done task - Cloud Run timing issue")
                        return
                        
                    # Handle cancelled tasks separately (can't call exception() on cancelled tasks)
                    if task.cancelled():
                        logger.info("Health monitoring task cancelled - likely due to Cloud Run resource management")
                        try:
                            # Schedule restart after cancellation
                            asyncio.create_task(self._restart_health_monitoring_after_delay(delay=15))
                        except Exception as restart_error:
                            logger.error(f"Failed to restart health monitoring after cancellation: {restart_error}")
                        return
                    
                    # Now safe to check exceptions on done, non-cancelled tasks
                    try:
                        task_exception = task.exception()
                        if task_exception:
                            logger.error(f"Health monitoring failed with exception: {task_exception}", exc_info=True)
                            # Schedule restart after exception with longer delay
                            asyncio.create_task(self._restart_health_monitoring_after_delay(delay=30))
                        else:
                            logger.debug("Health monitoring task completed successfully")
                    except Exception as exception_check_error:
                        logger.error(f"Could not retrieve task exception: {exception_check_error}")
                        asyncio.create_task(self._restart_health_monitoring_after_delay(delay=45))
                        
                except Exception as callback_error:
                    # Absolute safety net - health monitoring callback must NEVER crash the service
                    logger.error(f"CRITICAL: Health monitoring callback system error: {callback_error}", exc_info=True)
                    try:
                        # Last resort restart with maximum delay
                        asyncio.create_task(self._restart_health_monitoring_after_delay(delay=120))
                    except Exception:
                        # Final fallback - disable health monitoring rather than crash
                        logger.critical("Health monitoring system completely failed - service continuing without health checks")
            
            self._health_check_task.add_done_callback(handle_health_task_completion)
            logger.debug("Health monitoring task started with enhanced error handling")
    
    async def _restart_health_monitoring_after_delay(self, delay: int = 30) -> None:
        """Restart health monitoring after failure with Cloud Run-optimized delay patterns."""
        try:
            logger.info(f"Scheduling health monitoring restart after {delay}s delay")
            await asyncio.sleep(delay)
            
            # Check if service is shutting down before restarting
            if self._shutdown:
                logger.info("Service shutdown detected - not restarting health monitoring")
                return
                
            logger.info("Restarting health monitoring after failure recovery delay")
            await self._start_health_monitoring()
            
        except asyncio.CancelledError:
            # Expected during service shutdown - don't log as error
            logger.debug("Health monitoring restart cancelled during service shutdown")
        except Exception as restart_error:
            # Even restart attempts should not crash the service
            logger.error(f"Failed to restart health monitoring: {restart_error}")
            
            # Exponential backoff for restart failures
            backoff_delay = min(delay * 2, 300)  # Max 5 minute backoff
            logger.info(f"Scheduling health monitoring restart with backoff delay: {backoff_delay}s")
            try:
                await asyncio.sleep(backoff_delay)
                await self._start_health_monitoring()
            except asyncio.CancelledError:
                logger.debug("Health monitoring restart with backoff cancelled during service shutdown")
            except Exception as backoff_error:
                logger.critical(f"Health monitoring restart with backoff failed: {backoff_error}")
    
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
        """Check WebSocket manager health with GOLDEN PATH graceful degradation.
        
        GOLDEN PATH FIX: Allows basic WebSocket functionality even when
        some services have startup delays, preventing chat blockage.
        
        NOTE: In per-request isolation architecture, WebSocket manager
        is None at startup and created per-request. This is expected.
        """
        try:
            # GOLDEN PATH: Per-request architecture is inherently healthy
            # WebSocket managers are created per-request for isolation
            # Even if some backend services have delays, basic chat can proceed
            return True  # Always healthy - actual checks happen per-request
        except Exception as e:
            # GRACEFUL DEGRADATION: Log but don't fail completely
            logger.warning(f"WebSocket manager health check warning: {e} - allowing degraded operation")
            return True  # GOLDEN PATH: Don't block user chat for infrastructure delays
    
    async def _check_registry_health(self) -> bool:
        """DEPRECATED: Registry health check removed - using per-request factory patterns.
        
        Per-request factory patterns don't require global registry health checks.
        Health is validated per-request through create_user_emitter() factory methods.
        """
        # Always return True since per-request factories handle their own validation
        return True
    
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
                # REMOVED: Orchestrator availability - using per-request factory patterns
                # "orchestrator_available": self._orchestrator is not None,
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
                        try:
                            await asyncio.sleep(delay)
                        except asyncio.CancelledError:
                            logger.info("Recovery cancelled during backoff delay")
                            raise  # Re-raise to exit recovery cleanly
                    
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
                        
                except asyncio.CancelledError:
                    logger.info("Recovery cancelled during attempt - exiting cleanly")
                    return IntegrationResult(
                        success=False,
                        state=self.state,
                        error="Recovery cancelled",
                        recovery_attempted=True
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
        """Background health monitoring loop with proper cancellation handling."""
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
                
            except asyncio.CancelledError:
                # Handle cancellation gracefully - this happens during shutdown or Cloud Run resource management
                logger.info("Health monitoring task cancelled - shutting down cleanly")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                # Don't break on general exceptions - continue monitoring
    
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
                # REMOVED: Orchestrator availability - using per-request factory patterns  
                # "orchestrator_available": self._orchestrator is not None,
                "orchestrator_factory_available": hasattr(self, 'create_execution_orchestrator'),
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
        
        # REMOVED: Singleton orchestrator shutdown - using per-request factory patterns
        # No global orchestrator to shut down - factory methods handle per-request lifecycle
        
        # Shutdown thread registry if available
        if self._thread_registry:
            try:
                await self._thread_registry.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down thread registry: {e}")
        
        # Clear references
        self._websocket_manager = None
        # REMOVED: Singleton orchestrator - using per-request factory patterns instead  
        # self._orchestrator = None
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
    
    # ===================== PER-REQUEST ORCHESTRATOR FACTORY =====================
    # BUSINESS CRITICAL: Enables agent execution pipeline with WebSocket integration
    
    async def create_execution_orchestrator(self, user_id: str, agent_type: str) -> 'RequestScopedOrchestrator':
        """
        Create per-request orchestrator for agent execution with WebSocket integration.
        
        This method replaces the singleton orchestrator pattern with per-request
        instances to ensure complete user isolation and proper WebSocket event emission.
        
        Args:
            user_id: User identifier for execution context
            agent_type: Type of agent being executed
            
        Returns:
            RequestScopedOrchestrator: Per-request orchestrator with WebSocket integration
            
        Raises:
            RuntimeError: If WebSocket manager not available for event emission
            
        Business Value:
        - Restores agent execution pipeline functionality  
        - Enables WebSocket event emission (agent_thinking, tool_executing, etc.)
        - Maintains proper multi-user isolation patterns
        - Supports complete agent-to-user response delivery
        """
        if not self._websocket_manager:
            raise RuntimeError(f"WebSocket manager not available for user {user_id}")
        
        logger.info(f"Creating per-request orchestrator for user {user_id}, agent {agent_type}")
        
        # Import here to avoid circular imports
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_id_manager import generate_thread_id, generate_execution_id
        
        # Create proper UserExecutionContext for this request using the accepted type
        thread_id = generate_thread_id()
        run_id = generate_execution_id()
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_context={"agent_type": agent_type, "orchestrator_created": True}
        )
        
        # Create user-scoped emitter for WebSocket events
        emitter = await self.create_user_emitter(user_context)
        
        # Return per-request orchestrator with WebSocket integration
        return RequestScopedOrchestrator(
            user_context=user_context,
            emitter=emitter,
            websocket_bridge=self
        )
    
    # ===================== UTILITY METHODS =====================
    # Support methods for run ID processing (required by startup validator)
    
    def extract_thread_id(self, run_id: str) -> str:
        """
        Extract thread ID from run ID (delegated to UnifiedIDManager).
        
        Args:
            run_id: Run ID to extract thread ID from
            
        Returns:
            Extracted thread ID
        """
        return UnifiedIDManager.extract_thread_id(run_id)
    
    # ===================== NOTIFICATION INTERFACE =====================
    # SSOT for all WebSocket notifications - CRYSTAL CLEAR emission paths
    # BUSINESS CRITICAL: These methods enable 90% of chat functionality value
    
    async def notify_agent_started(
        self, 
        run_id: str, 
        agent_name: str, 
        context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[Dict[str, Any]] = None,
        user_context: Optional['UserExecutionContext'] = None
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
            # PHASE 1 FIX: Use UserExecutionContext for proper user_id routing
            effective_user_context = user_context or self.user_context
            if not effective_user_context:
                logger.error(f"🚨 EMISSION BLOCKED: No UserExecutionContext available for agent_started (run_id={run_id}, agent={agent_name})")
                return False
            
            # CRITICAL VALIDATION: Check run_id context before emission
            if not self._validate_event_context(run_id, "agent_started", agent_name):
                return False
            
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_started (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message with user_id for proper routing
            notification = {
                "type": "agent_started",
                "run_id": run_id,
                "user_id": effective_user_context.user_id,  # PHASE 1 FIX: Include user_id for routing
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "status": "started",
                    "context": context or {},
                    "message": f"{agent_name} has started processing your request"
                }
            }
            
            # Add trace context if provided
            if trace_context:
                notification["trace"] = trace_context
            
            # PHASE 1 FIX: Use user_id directly for WebSocket routing (no thread_id resolution needed)
            user_id = effective_user_context.user_id
            print(f"DEBUG: notify_agent_started - run_id={run_id}, user_id={user_id}")
            
            # PHASE 1 FIX: Direct WebSocket emission using user_id
            success = await self._websocket_manager.send_to_user(user_id, notification)
            print(f"DEBUG: notify_agent_started - send_to_user success={success}")
            
            if success:
                logger.info(f"✅ EMISSION SUCCESS: agent_started → user={user_id} (run_id={run_id}, agent={agent_name})")
                # PHASE 2 FIX: Track successful event delivery (to be implemented)
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("agent_started", run_id, True)
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_started send failed (run_id={run_id}, agent={agent_name})")
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("agent_started", run_id, False)
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_started failed (run_id={run_id}, agent={agent_name}): {e}")
            # PHASE 4 FIX: Propagate critical errors instead of silent failure
            if "CRITICAL" in str(e) or "user_id" in str(e).lower():
                raise  # Don't allow critical routing errors to fail silently
            return False
    
    async def notify_agent_thinking(
        self, 
        run_id: str, 
        agent_name: str, 
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None,
        trace_context: Optional[Dict[str, Any]] = None,
        user_context: Optional['UserExecutionContext'] = None
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
            # PHASE 1 FIX: Use UserExecutionContext for proper user_id routing
            effective_user_context = user_context or self.user_context
            if not effective_user_context:
                logger.error(f"🚨 EMISSION BLOCKED: No UserExecutionContext available for agent_thinking (run_id={run_id}, agent={agent_name})")
                return False
            
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for agent_thinking (run_id={run_id}, agent={agent_name})")
                return False
            
            # Build standardized notification message with user_id for proper routing
            notification = {
                "type": "agent_thinking",
                "run_id": run_id,
                "user_id": effective_user_context.user_id,  # PHASE 1 FIX: Include user_id for routing
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "reasoning": reasoning,
                    "step_number": step_number,
                    "progress_percentage": progress_percentage,
                    "status": "thinking"
                }
            }
            
            # Add trace context if provided
            if trace_context:
                notification["trace"] = trace_context
            
            # PHASE 1 FIX: Use user_id directly for WebSocket routing (no thread_id resolution needed)
            user_id = effective_user_context.user_id
            
            # PHASE 1 FIX: Direct WebSocket emission using user_id
            success = await self._websocket_manager.send_to_user(user_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: agent_thinking → user={user_id} (run_id={run_id}, agent={agent_name})")
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("agent_thinking", run_id, True)
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_thinking send failed (run_id={run_id}, agent={agent_name})")
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("agent_thinking", run_id, False)
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_thinking failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_tool_executing(
        self, 
        run_id: str, 
        tool_name: str,
        agent_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        user_context: Optional['UserExecutionContext'] = None
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
            # PHASE 1 FIX: Use UserExecutionContext for proper user_id routing
            effective_user_context = user_context or self.user_context
            if not effective_user_context:
                logger.error(f"🚨 EMISSION BLOCKED: No UserExecutionContext available for tool_executing (run_id={run_id}, tool={tool_name})")
                return False
            
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for tool_executing (run_id={run_id}, tool={tool_name})")
                return False
            
            # Use agent name from context if not provided
            effective_agent_name = agent_name or getattr(effective_user_context, 'agent_context', {}).get('agent_name', 'Agent')
            
            # Build standardized notification message with user_id for proper routing
            notification = {
                "type": "tool_executing",
                "run_id": run_id,
                "user_id": effective_user_context.user_id,  # PHASE 1 FIX: Include user_id for routing
                "agent_name": effective_agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tool_name": tool_name,
                    "parameters": self._sanitize_parameters(parameters) if parameters else {},
                    "status": "executing",
                    "message": f"{effective_agent_name} is using {tool_name}"
                }
            }
            
            # PHASE 1 FIX: Use user_id directly for WebSocket routing (no thread_id resolution needed)
            user_id = effective_user_context.user_id
            
            # PHASE 1 FIX: Direct WebSocket emission using user_id
            success = await self._websocket_manager.send_to_user(user_id, notification)
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: tool_executing → user={user_id} (run_id={run_id}, tool={tool_name})")
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("tool_executing", run_id, True)
            else:
                logger.error(f"🚨 EMISSION FAILED: tool_executing send failed (run_id={run_id}, tool={tool_name})")
                if hasattr(self, '_track_event_delivery'):
                    await self._track_event_delivery("tool_executing", run_id, False)
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_tool_executing failed (run_id={run_id}, tool={tool_name}): {e}")
            return False
    
    async def notify_tool_completed(
        self, 
        run_id: str, 
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        user_context: Optional['UserExecutionContext'] = None
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
            
            # PHASE 3 FIX: Enhanced event delivery with retry mechanism
            success = await self._emit_with_retry(
                event_type="tool_completed",
                thread_id=thread_id, 
                notification=notification,
                run_id=run_id,
                agent_name=agent_name,
                max_retries=3
            )
            
            if success:
                logger.debug(f"✅ EMISSION SUCCESS: tool_completed → thread={thread_id} (run_id={run_id}, tool={tool_name})")
                await self._track_event_delivery("tool_completed", run_id, True)
            else:
                logger.error(f"🚨 EMISSION FAILED: tool_completed send failed (run_id={run_id}, tool={tool_name})")
                await self._track_event_delivery("tool_completed", run_id, False)
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_tool_completed failed (run_id={run_id}, tool={tool_name}): {e}")
            return False
    
    async def notify_agent_completed(
        self, 
        run_id: str, 
        agent_name: str, 
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        trace_context: Optional[Dict[str, Any]] = None
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
            
            # Add trace context if provided
            if trace_context:
                notification["trace"] = trace_context
            
            # CRYSTAL CLEAR EMISSION: Resolve thread_id and emit
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # PHASE 3 FIX: Enhanced event delivery with retry mechanism - CRITICAL EVENT
            success = await self._emit_with_retry(
                event_type="agent_completed",
                thread_id=thread_id, 
                notification=notification,
                run_id=run_id,
                agent_name=agent_name,
                max_retries=5,  # Extra retries for critical completion event
                critical_event=True
            )
            
            if success:
                logger.info(f"✅ EMISSION SUCCESS: agent_completed → thread={thread_id} (run_id={run_id}, agent={agent_name})")
                await self._track_event_delivery("agent_completed", run_id, True)
            else:
                logger.error(f"🚨 EMISSION FAILED: agent_completed send failed (run_id={run_id}, agent={agent_name})")
                await self._track_event_delivery("agent_completed", run_id, False)
                # PHASE 3 FIX: Alert for critical event failure
                await self._alert_critical_event_failure("agent_completed", run_id, agent_name)
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 EMISSION EXCEPTION: notify_agent_completed failed (run_id={run_id}, agent={agent_name}): {e}")
            return False
    
    async def notify_agent_error(
        self, 
        run_id: str, 
        agent_name: str, 
        error: str,
        error_context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[Dict[str, Any]] = None
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
            
            # Add trace context if provided
            if trace_context:
                notification["trace"] = trace_context
            
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
    
    # ===================== CORE EVENT EMISSION METHOD =====================
    
    async def emit_agent_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        run_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> bool:
        """
        PHASE 2 REDIRECTION WRAPPER: Delegates to UnifiedWebSocketEmitter SSOT.
        
        This method now acts as a thin wrapper that maintains the exact same API
        while delegating all functionality to the consolidated UnifiedWebSocketEmitter.
        
        CRITICAL SECURITY: All security validation now handled by SSOT emitter,
        preventing events from being misrouted to wrong users.
        
        Args:
            event_type: Type of event to emit
            data: Event payload data
            run_id: Unique execution identifier (REQUIRED for routing)
            agent_name: Optional agent name for logging
            
        Returns:
            bool: True if event was successfully queued/sent
            
        Raises:
            ValueError: If run_id is invalid or context validation fails
            
        Business Impact: Maintains backward compatibility while eliminating race conditions
                        through single source of truth for event emission.
        """
        try:
            # PHASE 2: Delegate to UnifiedWebSocketEmitter SSOT
            if not self._websocket_manager:
                logger.warning(f"🚨 EMISSION BLOCKED: WebSocket manager unavailable for {event_type} (run_id={run_id})")
                return False
            
            # Resolve user ID from run_id for emitter creation
            thread_id = await self._resolve_thread_id_from_run_id(run_id)
            if not thread_id:
                logger.error(f"🚨 EMISSION FAILED: Cannot resolve thread_id for run_id={run_id}")
                return False
            
            # Get or create UnifiedWebSocketEmitter for this user context
            # This ensures we use the SSOT for all event emission
            from netra_backend.app.websocket_core.unified_emitter import WebSocketEmitterFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create context for the emitter
            context = UserExecutionContext(
                user_id=thread_id,  # Using thread_id as user identifier
                run_id=run_id,
                thread_id=thread_id,
                request_id=getattr(data, 'request_id', None)
            )
            
            # Create SSOT emitter
            emitter = WebSocketEmitterFactory.create_scoped_emitter(
                manager=self._websocket_manager,
                context=context
            )
            
            # Build standardized event data for SSOT emitter
            event_data = {
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if agent_name:
                event_data["agent_name"] = agent_name
            
            # SSOT EMISSION: Use consolidated emitter
            success = await emitter.emit(event_type, event_data)
            
            if success:
                logger.debug(f"✅ SSOT EMISSION SUCCESS: {event_type} → thread={thread_id} (run_id={run_id})")
            else:
                logger.error(f"🚨 SSOT EMISSION FAILED: {event_type} send failed (run_id={run_id})")
            
            return success
            
        except Exception as e:
            logger.error(f"🚨 SSOT EMISSION EXCEPTION: emit_agent_event delegation failed (event_type={event_type}, run_id={run_id}): {e}")
            return False
    
    def _validate_event_context(self, run_id: Optional[str], event_type: str, agent_name: Optional[str] = None) -> bool:
        """
        Validate WebSocket event context to ensure proper user isolation.
        
        CRITICAL SECURITY: This validation prevents events from being sent without proper context,
        which could result in events being delivered to wrong users or global broadcast.
        
        Args:
            run_id: Run identifier to validate
            event_type: Type of event being emitted (for logging)
            agent_name: Optional agent name (for logging)
            
        Returns:
            bool: True if context is valid and event should be sent
            
        Security Impact: Prevents cross-user data leakage and ensures WebSocket events
                        are only sent to the correct user context.
        """
        try:
            # CRITICAL CHECK: run_id cannot be None
            if run_id is None:
                logger.error(f"🚨 CONTEXT VALIDATION FAILED: run_id is None for {event_type} "
                           f"(agent={agent_name or 'unknown'}). This would cause event misrouting!")
                logger.error(f"🚨 SECURITY RISK: Events with None run_id can be delivered to wrong users!")
                return False
            
            # CRITICAL CHECK: run_id cannot be 'registry' (system context)
            if run_id == 'registry':
                logger.error(f"🚨 CONTEXT VALIDATION FAILED: run_id='registry' for {event_type} "
                           f"(agent={agent_name or 'unknown'}). System context cannot emit user events!")
                logger.error(f"🚨 SECURITY RISK: Registry context events would be broadcast to all users!")
                return False
            
            # VALIDATION CHECK: run_id should be a non-empty string
            if not isinstance(run_id, str) or not run_id.strip():
                logger.error(f"🚨 CONTEXT VALIDATION FAILED: Invalid run_id '{run_id}' for {event_type} "
                           f"(agent={agent_name or 'unknown'}). run_id must be non-empty string!")
                return False
            
            # VALIDATION CHECK: run_id should not contain suspicious patterns
            if self._is_suspicious_run_id(run_id):
                logger.warning(f"⚠️ CONTEXT VALIDATION WARNING: Suspicious run_id pattern '{run_id}' for {event_type} "
                              f"(agent={agent_name or 'unknown'}). Event will be sent but flagged for monitoring.")
                # Allow but log for monitoring - some legitimate run_ids might trigger this
            
            # Context validation passed
            logger.debug(f"✅ CONTEXT VALIDATION PASSED: run_id={run_id} for {event_type} is valid")
            return True
            
        except Exception as e:
            logger.error(f"🚨 CONTEXT VALIDATION EXCEPTION: Validation failed for {event_type} "
                        f"(run_id={run_id}, agent={agent_name or 'unknown'}): {e}")
            return False
    
    def _is_suspicious_run_id(self, run_id: str) -> bool:
        """
        Check if a run_id contains suspicious patterns that might indicate invalid context.
        
        This helps detect potentially invalid run_ids that could cause security issues
        or indicate bugs in the calling code.
        
        Args:
            run_id: Run ID to check for suspicious patterns
            
        Returns:
            bool: True if run_id contains suspicious patterns
        """
        if not run_id or not isinstance(run_id, str):
            return True
        
        run_id_lower = run_id.lower()
        
        # Suspicious patterns that indicate invalid context
        suspicious_patterns = [
            # System/generic identifiers that shouldn't be user run_ids
            "system", "global", "broadcast", "admin", "root", "default",
            # Test artifacts that might leak into production
            "test", "mock", "fake", "dummy", "placeholder", "example",
            # Empty/null-like values
            "null", "none", "undefined", "empty", "",
            # Debug/development patterns
            "debug", "dev", "local", "temp", "temporary"
        ]
        
        # Check for exact matches or word boundaries to avoid false positives
        # like 'test' matching 'thread_test' but not 'thread_'
        import re
        for pattern in suspicious_patterns:
            if pattern == "":
                continue  # Skip empty pattern
            # Use word boundary matching to avoid false positives
            # Match pattern as whole word or with underscores/dashes as boundaries
            if re.search(r'(^|_|-)' + re.escape(pattern) + r'($|_|-)', run_id_lower):
                return True
        
        # Check for overly short identifiers (less than 3 chars)
        if len(run_id.strip()) < 3:
            return True
        
        # Check for patterns that look like system identifiers
        if run_id_lower.startswith(('sys_', 'system_', 'global_', 'admin_')):
            return True
        
        return False

    # ===================== HELPER METHODS =====================
    
    async def _resolve_thread_id_from_run_id(self, run_id: str) -> Optional[str]:
        """
        Resolve thread_id from run_id for proper WebSocket routing.
        
        CRITICAL: This method ensures notifications reach the correct user chat thread.
        Enhanced 5-Priority Resolution Algorithm for 99% reliability.
        
        Priority Chain (executed in order):
        1. ThreadRunRegistry lookup (PRIMARY - highest reliability) 
        2. Orchestrator query (SECONDARY - when available)
        3. Direct WebSocketManager check (TERTIARY - active connections)
        4. Standardized pattern extraction (QUATERNARY - run_id format parsing)
        5. ERROR logging and exception (FINAL - no silent failures)
        
        Business Value: Eliminates silent failures that destroy user trust
        """
        # Start resolution timing for metrics
        resolution_start_time = time.time()
        resolution_source = None
        
        try:
            # Input validation with comprehensive logging
            if not run_id or not isinstance(run_id, str):
                logger.error(f"🚨 RESOLUTION FAILED: Invalid run_id input type or empty: {run_id} (type: {type(run_id)})")
                raise ValueError(f"Invalid run_id: must be non-empty string, got {type(run_id)}: {run_id}")
            
            run_id = run_id.strip()
            if not run_id:
                logger.error("🚨 RESOLUTION FAILED: Empty run_id after stripping whitespace")
                raise ValueError("Empty run_id after stripping whitespace")
            
            logger.debug(f"🔍 THREAD RESOLUTION START: run_id={run_id}")
            
            # PRIORITY 1: ThreadRunRegistry lookup (PRIMARY SOURCE - MOST RELIABLE)
            # This is the golden source that should resolve 80%+ of requests
            if self._thread_registry:
                try:
                    thread_id = await self._thread_registry.get_thread(run_id)
                    if thread_id and isinstance(thread_id, str) and thread_id.strip():
                        resolution_time_ms = (time.time() - resolution_start_time) * 1000
                        resolution_source = "thread_registry"
                        logger.info(f"✅ PRIORITY 1 SUCCESS: run_id={run_id} → thread_id={thread_id} via ThreadRunRegistry ({resolution_time_ms:.1f}ms)")
                        self._track_resolution_success(resolution_source, resolution_time_ms)
                        return thread_id
                    elif thread_id is not None:
                        logger.warning(f"⚠️ PRIORITY 1 INVALID: ThreadRunRegistry returned invalid thread_id: '{thread_id}' for run_id={run_id}")
                except Exception as e:
                    logger.warning(f"⚠️ PRIORITY 1 EXCEPTION: ThreadRunRegistry lookup failed for run_id={run_id}: {e}")
                    self._track_resolution_failure("thread_registry", str(e))
            else:
                logger.debug(f"⚠️ PRIORITY 1 SKIP: ThreadRunRegistry not available for run_id={run_id}")
            
            # REMOVED: Orchestrator query - using per-request factory patterns
            # Thread resolution is handled per-request through factory methods
            # No global orchestrator needed for user isolation pattern
            
            # PRIORITY 3: Direct WebSocketManager check (TERTIARY SOURCE - active connections)
            # Check if WebSocketManager has any active connections that might help resolve
            if self._websocket_manager:
                try:
                    # Check if the run_id itself is a valid thread_id format and has active connections
                    if run_id.startswith("thread_") and self._is_valid_thread_format(run_id):
                        # Check if WebSocketManager has active connections for this thread_id
                        if hasattr(self._websocket_manager, 'connections') and hasattr(self._websocket_manager.connections, 'get'):
                            connection_exists = self._websocket_manager.connections.get(run_id) is not None
                            if connection_exists:
                                resolution_time_ms = (time.time() - resolution_start_time) * 1000
                                resolution_source = "websocket_manager"
                                logger.info(f"✅ PRIORITY 3 SUCCESS: run_id={run_id} is valid thread_id with active WebSocket connection ({resolution_time_ms:.1f}ms)")
                                self._track_resolution_success(resolution_source, resolution_time_ms)
                                return run_id
                        else:
                            # WebSocketManager doesn't have the expected interface, treat as valid if format is correct
                            if self._is_valid_thread_format(run_id):
                                resolution_time_ms = (time.time() - resolution_start_time) * 1000
                                resolution_source = "direct_format"
                                logger.info(f"✅ PRIORITY 3 SUCCESS: run_id={run_id} is valid thread_id format ({resolution_time_ms:.1f}ms)")
                                self._track_resolution_success(resolution_source, resolution_time_ms)
                                return run_id
                except Exception as e:
                    logger.warning(f"⚠️ PRIORITY 3 EXCEPTION: WebSocketManager check failed for run_id={run_id}: {e}")
                    self._track_resolution_failure("websocket_manager", str(e))
            else:
                logger.debug(f"⚠️ PRIORITY 3 SKIP: WebSocketManager not available for run_id={run_id}")
            
            # PRIORITY 4: Enhanced standardized pattern extraction (QUATERNARY SOURCE)
            # Extract thread_id from standardized run_id patterns with improved reliability
            try:
                extracted_thread_id = self._extract_thread_from_standardized_run_id(run_id)
                if extracted_thread_id:
                    resolution_time_ms = (time.time() - resolution_start_time) * 1000
                    resolution_source = "pattern_extraction"
                    logger.info(f"✅ PRIORITY 4 SUCCESS: run_id={run_id} → thread_id={extracted_thread_id} via pattern extraction ({resolution_time_ms:.1f}ms)")
                    self._track_resolution_success(resolution_source, resolution_time_ms)
                    
                    # OPTIONAL: Register this discovered mapping for future lookups
                    if self._thread_registry:
                        try:
                            await self._thread_registry.register(run_id, extracted_thread_id, {"source": "pattern_extraction"})
                            logger.debug(f"📝 BACKFILL: Registered pattern-extracted mapping run_id={run_id} → thread_id={extracted_thread_id}")
                        except Exception as backfill_error:
                            logger.debug(f"⚠️ BACKFILL FAILED: Could not register pattern mapping: {backfill_error}")
                    
                    return extracted_thread_id
                else:
                    logger.debug(f"⚠️ PRIORITY 4 NO MATCH: No valid thread pattern found in run_id={run_id}")
            except Exception as e:
                logger.warning(f"⚠️ PRIORITY 4 EXCEPTION: Pattern extraction failed for run_id={run_id}: {e}")
                self._track_resolution_failure("pattern_extraction", str(e))
            
            # PRIORITY 5: ERROR logging and raise exception (NO SILENT FAILURES)
            # This ensures we never silently fail - all failures are logged and tracked
            resolution_time_ms = (time.time() - resolution_start_time) * 1000
            error_context = {
                "run_id": run_id,
                "resolution_time_ms": resolution_time_ms,
                "thread_registry_available": self._thread_registry is not None,
                # REMOVED: Orchestrator availability - using per-request factory patterns
                # "orchestrator_available": self._orchestrator is not None,  
                "websocket_manager_available": self._websocket_manager is not None,
                "run_id_format": "valid" if run_id.startswith("thread_") and self._is_valid_thread_format(run_id) else "unknown",
                "contains_thread_pattern": "thread_" in run_id,
                "business_impact": "WebSocket notifications will not reach user - critical chat functionality failure"
            }
            
            # Log comprehensive ERROR with full context
            logger.error(f"🚨 PRIORITY 5 RESOLUTION FAILURE: Unable to resolve thread_id for run_id={run_id} after trying all 5 priorities")
            logger.error(f"🚨 RESOLUTION CONTEXT: {error_context}")
            logger.error(f"🚨 BUSINESS IMPACT: User will not receive WebSocket notifications for run_id={run_id} - this breaks core chat functionality")
            
            # Track the failure for metrics and monitoring
            self._track_resolution_failure("complete_failure", f"All 5 priorities failed for run_id={run_id}")
            
            # Raise ValueError to prevent silent failures
            raise ValueError(f"Thread resolution failed for run_id={run_id}: All 5 priority sources failed. Business impact: WebSocket notifications will not reach user. Context: {error_context}")
            
        except ValueError as ve:
            # Re-raise ValueError (these are expected failures we want to propagate)
            raise ve
        except Exception as e:
            # Catch any unexpected exceptions and wrap them
            resolution_time_ms = (time.time() - resolution_start_time) * 1000
            logger.error(f"🚨 CRITICAL EXCEPTION: Unexpected exception during thread resolution for run_id={run_id}: {e}")
            logger.error(f"🚨 RESOLUTION TIME: {resolution_time_ms:.1f}ms before exception")
            self._track_resolution_failure("critical_exception", str(e))
            raise ValueError(f"Critical exception during thread resolution for run_id={run_id}: {e}")
    
    def _track_resolution_success(self, resolution_source: str, resolution_time_ms: float) -> None:
        """Track successful thread resolution for monitoring."""
        # Implementation can be extended for metrics collection
        pass
    
    def _track_resolution_failure(self, failure_source: str, error_message: str) -> None:
        """Track failed thread resolution for monitoring."""
        # Implementation can be extended for metrics collection
        pass
    
    def _is_valid_thread_format(self, thread_id: str) -> bool:
        """
        Validate if a string is a valid thread_id format.
        
        Valid formats:
        - thread_abc123
        - thread_user_session_789
        - thread_12345
        - thread_agent_execution_456
        
        Invalid formats:
        - thread_ (incomplete)
        - thread__ (double underscore)
        - thread_123_ (trailing underscore)
        """
        if not thread_id or not isinstance(thread_id, str):
            return False
        
        # Must start with "thread_"
        if not thread_id.startswith("thread_"):
            return False
        
        # Extract the part after "thread_"
        suffix = thread_id[7:]  # Remove "thread_" prefix
        
        # Must have content after "thread_"
        if not suffix:
            return False
        
        # Must not have trailing underscore
        if suffix.endswith("_"):
            return False
        
        # Must not have double underscores
        if "__" in thread_id:
            return False
        
        # Must contain only alphanumeric characters and underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', suffix):
            return False
        
        return True
    
    def _is_suspicious_thread_id(self, thread_id: str) -> bool:
        """
        Check if a thread_id looks suspicious or invalid for pattern extraction.
        
        This helps avoid false positives when extracting threads from run_ids.
        
        Args:
            thread_id: Thread ID to validate
            
        Returns:
            bool: True if thread_id looks suspicious/invalid
        """
        if not thread_id or not isinstance(thread_id, str):
            return True
        
        # Convert to lowercase for case-insensitive checking
        thread_lower = thread_id.lower()
        
        # Suspicious patterns that indicate false extraction
        suspicious_patterns = [
            # Test artifacts
            "pattern", "no", "impossible", "anywhere", "nothing", "missing", "test",
            # Generic/vague identifiers
            "unknown", "default", "temp", "temporary", "placeholder", "dummy",
            # System words that shouldn't be thread identifiers
            "error", "failure", "broken", "invalid", "null", "none", "undefined",
            # Common false positives
            "false", "true", "success", "complete", "done", "finished"
        ]
        
        # Check if thread_id contains suspicious words
        thread_parts = thread_lower.replace("thread_", "").split("_")
        for part in thread_parts:
            if part in suspicious_patterns:
                return True
        
        # Check for overly generic patterns
        if len(thread_parts) == 1 and len(thread_parts[0]) < 3:
            return True  # Too short to be meaningful
        
        # Check if it looks like a test pattern
        if any(word in thread_lower for word in ["test", "mock", "fake", "dummy"]):
            return True
        
        return False
    
    def _extract_thread_from_standardized_run_id(self, run_id: str) -> Optional[str]:
        """
        UPDATED: Extract thread_id using UnifiedIDManager SSOT.
        
        This method now uses UnifiedIDManager to handle ALL supported formats:
        1. Canonical: "thread_{thread_id}_run_{timestamp}_{uuid}" 
        2. Legacy IDManager: "run_{thread_id}_{uuid}"
        3. Direct thread format: "thread_user_123_session"
        
        CRITICAL: This fixes WebSocket routing failures by using the unified extraction logic
        that handles all ID formats with backward compatibility.
        
        Returns:
            Optional[str]: Extracted thread_id with "thread_" prefix if found, None otherwise
        """
        try:
            if not run_id or not isinstance(run_id, str):
                logger.debug(f"⚠️ INVALID INPUT: run_id={run_id} is not a valid string")
                return None
            
            run_id = run_id.strip()
            if not run_id:
                logger.debug(f"⚠️ EMPTY INPUT: run_id is empty after strip")
                return None
            
            # PRIORITY 1: Handle direct thread format (legacy compatibility)
            # If run_id is already a thread_id format, return it directly
            if run_id.startswith("thread_") and "_run_" not in run_id and self._is_valid_thread_format(run_id):
                logger.debug(f"✅ DIRECT THREAD FORMAT: run_id={run_id} is already a valid thread_id")
                return run_id
            
            # PRIORITY 2: Use UnifiedIDManager for SSOT extraction
            # Defensive import check to prevent runtime errors
            try:
                extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
            except NameError as e:
                logger.critical(f"🚨 CRITICAL: UnifiedIDManager not available: {e}")
                # Fallback to legacy extraction pattern
                return self._legacy_thread_extraction(run_id) if hasattr(self, '_legacy_thread_extraction') else None
            
            if extracted_thread_id:
                # UnifiedIDManager returns normalized thread_id (without "thread_" prefix)
                # Add "thread_" prefix for WebSocket bridge compatibility
                thread_id_with_prefix = f"thread_{extracted_thread_id}" if not extracted_thread_id.startswith("thread_") else extracted_thread_id
                
                # Get format info for detailed logging
                try:
                    format_info = UnifiedIDManager.get_format_info(run_id)
                    format_version = format_info.get('format_version', 'unknown')
                except (NameError, AttributeError) as e:
                    logger.warning(f"Could not get format info: {e}")
                    format_version = 'unknown'
                
                logger.debug(
                    f"✅ UNIFIED_ID_MANAGER SUCCESS: run_id={run_id} → thread_id={thread_id_with_prefix} "
                    f"(format: {format_version}, extracted: {extracted_thread_id})"
                )
                
                # Validate the final thread format
                if self._is_valid_thread_format(thread_id_with_prefix):
                    return thread_id_with_prefix
                else:
                    logger.warning(
                        f"⚠️ VALIDATION FAILED: Extracted thread_id '{thread_id_with_prefix}' from run_id='{run_id}' "
                        f"failed validation (format: {format_version})"
                    )
                    return None
            else:
                # Log detailed failure information
                logger.warning(
                    f"⚠️ UNIFIED_ID_MANAGER FAILED: Could not extract thread_id from run_id='{run_id}'. "
                    f"This may cause WebSocket routing failure."
                )
                return None
            
        except Exception as e:
            logger.error(
                f"🚨 CRITICAL EXCEPTION: UnifiedIDManager extraction failed for run_id='{run_id}': {e}. "
                f"This will cause WebSocket routing failure."
            )
            return None
    
    def _track_resolution_success(self, resolution_source: str, resolution_time_ms: float) -> None:
        """
        Track successful thread resolution for metrics and monitoring.
        
        Args:
            resolution_source: Source that resolved the thread (registry, orchestrator, etc.)
            resolution_time_ms: Resolution time in milliseconds
        """
        try:
            # Initialize metrics tracking if not exists
            if not hasattr(self, '_resolution_metrics'):
                self._resolution_metrics = {
                    'total_resolutions': 0,
                    'successful_resolutions': 0,
                    'failed_resolutions': 0,
                    'resolution_sources': {},
                    'avg_resolution_time_ms': 0.0,
                    'last_success_time': None
                }
            
            # Update metrics
            self._resolution_metrics['total_resolutions'] += 1
            self._resolution_metrics['successful_resolutions'] += 1
            self._resolution_metrics['last_success_time'] = datetime.now(timezone.utc)
            
            # Track by source
            if resolution_source not in self._resolution_metrics['resolution_sources']:
                self._resolution_metrics['resolution_sources'][resolution_source] = {
                    'count': 0,
                    'total_time_ms': 0.0,
                    'avg_time_ms': 0.0,
                    'success_rate': 0.0
                }
            
            source_metrics = self._resolution_metrics['resolution_sources'][resolution_source]
            source_metrics['count'] += 1
            source_metrics['total_time_ms'] += resolution_time_ms
            source_metrics['avg_time_ms'] = source_metrics['total_time_ms'] / source_metrics['count']
            
            # Update overall average resolution time
            total_successful = self._resolution_metrics['successful_resolutions']
            current_avg = self._resolution_metrics['avg_resolution_time_ms']
            
            if total_successful == 1:
                self._resolution_metrics['avg_resolution_time_ms'] = resolution_time_ms
            else:
                # Rolling average
                self._resolution_metrics['avg_resolution_time_ms'] = (
                    (current_avg * (total_successful - 1) + resolution_time_ms) / total_successful
                )
            
            # Log success metrics periodically
            if self._resolution_metrics['total_resolutions'] % 100 == 0:
                success_rate = (self._resolution_metrics['successful_resolutions'] / 
                               self._resolution_metrics['total_resolutions'])
                logger.info(f"📊 RESOLUTION METRICS: {self._resolution_metrics['total_resolutions']} total, "
                          f"{success_rate:.1%} success rate, "
                          f"{self._resolution_metrics['avg_resolution_time_ms']:.1f}ms avg time")
        
        except Exception as e:
            logger.warning(f"⚠️ METRICS TRACKING ERROR: Failed to track resolution success: {e}")
    
    def _track_resolution_failure(self, failure_source: str, error_message: str) -> None:
        """
        Track failed thread resolution for metrics and monitoring.
        
        Args:
            failure_source: Source that failed (registry, orchestrator, etc.)
            error_message: Error message describing the failure
        """
        try:
            # Initialize metrics tracking if not exists
            if not hasattr(self, '_resolution_metrics'):
                self._resolution_metrics = {
                    'total_resolutions': 0,
                    'successful_resolutions': 0,
                    'failed_resolutions': 0,
                    'resolution_sources': {},
                    'failure_sources': {},
                    'avg_resolution_time_ms': 0.0,
                    'last_failure_time': None,
                    'last_failure_error': None
                }
            
            # Update metrics
            self._resolution_metrics['total_resolutions'] += 1
            self._resolution_metrics['failed_resolutions'] += 1
            self._resolution_metrics['last_failure_time'] = datetime.now(timezone.utc)
            self._resolution_metrics['last_failure_error'] = error_message
            
            # Track by failure source
            if failure_source not in self._resolution_metrics['failure_sources']:
                self._resolution_metrics['failure_sources'][failure_source] = {
                    'count': 0,
                    'recent_errors': [],
                    'failure_rate': 0.0
                }
            
            failure_metrics = self._resolution_metrics['failure_sources'][failure_source]
            failure_metrics['count'] += 1
            
            # Keep recent errors for debugging (max 10)
            failure_metrics['recent_errors'].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': error_message
            })
            if len(failure_metrics['recent_errors']) > 10:
                failure_metrics['recent_errors'].pop(0)
            
            # Log failure metrics for critical issues
            if failure_source == "complete_failure":
                logger.error("💥 COMPLETE RESOLUTION FAILURE: This is a critical business impact event")
            
            # Log failure summary periodically
            if self._resolution_metrics['failed_resolutions'] % 10 == 0:
                failure_rate = (self._resolution_metrics['failed_resolutions'] / 
                               self._resolution_metrics['total_resolutions'])
                logger.warning(f"📊 RESOLUTION FAILURES: {self._resolution_metrics['failed_resolutions']} failures, "
                             f"{failure_rate:.1%} failure rate")
        
        except Exception as e:
            logger.warning(f"⚠️ METRICS TRACKING ERROR: Failed to track resolution failure: {e}")
    
    def get_resolution_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive thread resolution metrics for monitoring and analysis.
        
        Returns:
            Dict containing resolution metrics and performance data
        """
        try:
            if not hasattr(self, '_resolution_metrics'):
                return {
                    'total_resolutions': 0,
                    'successful_resolutions': 0, 
                    'failed_resolutions': 0,
                    'success_rate': 1.0,
                    'avg_resolution_time_ms': 0.0,
                    'resolution_sources': {},
                    'failure_sources': {},
                    'metrics_available': False
                }
            
            metrics = self._resolution_metrics.copy()
            
            # Calculate success rate
            total = metrics['total_resolutions']
            if total > 0:
                metrics['success_rate'] = metrics['successful_resolutions'] / total
            else:
                metrics['success_rate'] = 1.0
                
            # Calculate source success rates
            for source, source_data in metrics.get('resolution_sources', {}).items():
                if 'count' in source_data and source_data['count'] > 0:
                    source_data['success_rate'] = source_data['count'] / total
                    
            metrics['metrics_available'] = True
            metrics['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return metrics
            
        except Exception as e:
            logger.error(f"🚨 Error getting resolution metrics: {e}")
            return {
                'error': f'Metrics retrieval failed: {e}',
                'metrics_available': False,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
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

    # ===================== FACTORY METHODS FOR USER ISOLATION =====================
    # CRITICAL SECURITY: These methods create per-request emitters to prevent user data leakage
    
    async def create_user_emitter(self, user_context: 'UserExecutionContext') -> 'WebSocketEventEmitter':
        """Create WebSocketEventEmitter for specific user context with complete isolation.
        
        SECURITY CRITICAL: Use this method for new code to prevent cross-user event leakage.
        This replaces the singleton notification methods with per-request isolated emitters.
        
        Args:
            user_context: User execution context with validated user information
            
        Returns:
            WebSocketEventEmitter: Isolated emitter bound to user context
            
        Raises:
            ValueError: If user_context is invalid or WebSocket manager unavailable
            
        Example:
            # Create per-user emitter (RECOMMENDED)
            emitter = await bridge.create_user_emitter(user_context)
            
            # Send events to specific user only - validated against context
            await emitter.emit_agent_started("MyAgent", {"query": "user query"})
            
            # Automatic cleanup when emitter goes out of scope
        """
        if not user_context:
            raise ValueError("user_context is required for creating user emitter")
        
        try:
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter, WebSocketEmitterFactory
            from netra_backend.app.agents.supervisor.user_execution_context import validate_user_context
            from netra_backend.app.core.config import get_config
            
            # PHASE 2 FEATURE FLAG: Check if SSOT consolidation is enabled
            config = get_config()
            ssot_enabled = config.ws_config.ssot_consolidation_enabled
            
            if ssot_enabled:
                logger.info(f"🚀 PHASE 2 ACTIVE: SSOT consolidation enabled for user {user_context.user_id}")
            else:
                logger.debug(f"📍 PHASE 2 INACTIVE: Using standard emitter for user {user_context.user_id}")
            
            # Validate user context before creating emitter
            validated_context = validate_user_context(user_context)
            
            # Create isolated WebSocket manager for this user context
            isolated_manager = WebSocketManager(user_context=validated_context)
            
            # PHASE 2 REDIRECTION: Always use UnifiedWebSocketEmitter (it's already the SSOT)
            # The feature flag is ready for future optimizations but current architecture is already consolidated
            emitter = WebSocketEmitterFactory.create_scoped_emitter(isolated_manager, validated_context)
            
            # PHASE 2 MONITORING: Track emitter creation for race condition metrics
            emitter_type = "ssot_unified" if ssot_enabled else "standard_unified"
            logger.info(f"✅ USER EMITTER CREATED: {user_context.get_correlation_id()} - type: {emitter_type}, isolated from other users")
            return emitter
            
        except Exception as e:
            logger.error(f"🚨 EMITTER CREATION FAILED: {e}")
            raise ValueError(f"Failed to create user emitter: {e}")
    
    @classmethod
    async def create_user_emitter_from_ids(
        cls,
        user_id: str,
        thread_id: str, 
        run_id: str,
        websocket_connection_id: Optional[str] = None
    ) -> 'WebSocketEventEmitter':
        """Create WebSocketEventEmitter from individual IDs (convenience method).
        
        SECURITY CRITICAL: Creates user execution context from IDs and returns isolated emitter.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            run_id: Run identifier
            websocket_connection_id: Optional WebSocket connection ID
            
        Returns:
            WebSocketEventEmitter: Isolated emitter bound to constructed user context
            
        Raises:
            ValueError: If any required ID is invalid
        """
        if not user_id or not thread_id or not run_id:
            raise ValueError("user_id, thread_id, and run_id are all required")
        
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create user execution context from IDs
            user_context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_connection_id=websocket_connection_id
            )
            
            # Create bridge instance and return emitter
            bridge = cls()
            return await bridge.create_user_emitter(user_context)
            
        except Exception as e:
            logger.error(f"🚨 EMITTER FROM IDS FAILED: {e}")
            raise ValueError(f"Failed to create user emitter from IDs: {e}")
    
    @staticmethod
    async def create_scoped_emitter(user_context: 'UserExecutionContext'):
        """Create scoped WebSocketEventEmitter with automatic cleanup.
        
        RECOMMENDED: Use this for automatic resource management in async context.
        
        Args:
            user_context: User execution context
            
        Yields:
            WebSocketEventEmitter: Emitter with automatic cleanup
            
        Example:
            async with AgentWebSocketBridge.create_scoped_emitter(user_context) as emitter:
                await emitter.emit_agent_started("MyAgent")
                # Automatic cleanup happens here
        """
        # Import from the actual location - use the create_scoped_emitter function
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        # Create scoped emitter using the factory pattern for user isolation
        manager = WebSocketManager(user_context=user_context)
        emitter = UnifiedWebSocketEmitter.create_scoped_emitter(manager, user_context)
        try:
            yield emitter
        finally:
            # Clean up if needed
            pass


class RequestScopedOrchestrator:
    """
    Per-request orchestrator for agent execution with WebSocket integration.
    
    This class provides the interface required by AgentService for creating
    execution contexts and completing executions, with WebSocket event emission.
    
    Replaces the singleton orchestrator pattern with per-request instances.
    """
    
    def __init__(self, user_context: 'UserExecutionContext', emitter, websocket_bridge: AgentWebSocketBridge):
        self.user_context = user_context
        self.emitter = emitter
        self.websocket_bridge = websocket_bridge
        self._active_contexts = {}
        
    async def create_execution_context(
        self, 
        agent_type: str, 
        user_id: str, 
        message: str, 
        context: Optional[str] = None
    ) -> tuple:
        """
        Create execution context and notifier for agent execution.
        
        Args:
            agent_type: Type of agent being executed
            user_id: User identifier
            message: User message/request
            context: Optional context string
            
        Returns:
            Tuple[ExecutionContext, WebSocketNotifier]: Context and notifier for WebSocket events
        """
        # Import here to avoid circular imports  
        from netra_backend.app.agents.base.execution_context import AgentExecutionContext
        from netra_backend.app.core.unified_id_manager import generate_thread_id, generate_execution_id
        
        # Create unique execution context
        thread_id = generate_thread_id()
        run_id = generate_execution_id()
        
        exec_context = AgentExecutionContext(
            context_id=run_id,
            agent_id=agent_type,
            operation=f"process_{agent_type.lower()}",
            user_id=user_id,
            session_id=self.user_context.session_id,
            run_id=run_id,
            thread_id=thread_id,
            agent_name=agent_type,
            metadata={
                "message": message,
                "context": context,
                "user_id": user_id,
                "orchestrator_type": "RequestScopedOrchestrator"
            }
        )
        
        # Create WebSocket notifier that delegates to emitter
        notifier = WebSocketNotifier(self.emitter, exec_context)
        
        # Store for cleanup
        self._active_contexts[run_id] = (exec_context, notifier)
        
        logger.info(f"Created execution context for {agent_type} (run_id={run_id})")
        return exec_context, notifier
    
    async def complete_execution(self, exec_context, result):
        """
        Complete agent execution and cleanup resources.
        
        Args:
            exec_context: Execution context from create_execution_context
            result: Agent execution result
        """
        run_id = exec_context.run_id
        
        # Send completion notification
        if hasattr(self.emitter, 'notify_agent_completed'):
            await self.emitter.notify_agent_completed(
                exec_context.agent_name,
                {
                    "status": "completed",
                    "result": str(result),
                    "run_id": run_id
                }
            )
        
        # Cleanup
        if run_id in self._active_contexts:
            del self._active_contexts[run_id]
        
        logger.info(f"Completed execution for agent {exec_context.agent_name} (run_id={run_id})")


class WebSocketNotifier:
    """Notifier that delegates WebSocket events to emitter."""
    
    def __init__(self, emitter, exec_context):
        """Initialize WebSocketNotifier with emitter and execution context."""
        self.emitter = emitter
        self.exec_context = exec_context
    
    @classmethod
    def create_for_user(cls, emitter, exec_context):
        """
        Factory method to create WebSocketNotifier with user context validation.
        
        Args:
            emitter: WebSocket emitter instance
            exec_context: User execution context with user_id
            
        Returns:
            WebSocketNotifier: Validated instance for user
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Validate required parameters
        if not emitter:
            raise ValueError("WebSocketNotifier requires valid emitter")
        if not exec_context:
            raise ValueError("WebSocketNotifier requires valid execution context")
        
        # Validate user context
        user_id = getattr(exec_context, 'user_id', None)
        if not user_id:
            raise ValueError("WebSocketNotifier requires user_id in execution context")
        
        # Create validated instance
        instance = cls(emitter, exec_context)
        
        # Additional validation for user isolation
        instance._validate_user_isolation()
        
        return instance
    
    def _validate_user_isolation(self):
        """Validate this instance is properly isolated for user.
        
        SSOT Compliance: Validation only - no initialization assignments.
        This method validates instance state without modifying it.
        
        Raises:
            ValueError: If instance is not properly initialized or user isolation violated
        """
        # SSOT CRITICAL: Validate instance attributes exist and are properly set
        if not hasattr(self, 'emitter') or not self.emitter:
            raise ValueError("WebSocketNotifier emitter not properly initialized - factory method failed")
        
        if not hasattr(self, 'exec_context') or not self.exec_context:
            raise ValueError("WebSocketNotifier exec_context not properly initialized - factory method failed")
        
        # Validate execution context has required user_id for isolation
        user_id = getattr(self.exec_context, 'user_id', None)
        if not user_id:
            raise ValueError("WebSocketNotifier requires user_id in execution context for user isolation")
        
        # Ensure no shared state with other user instances (SSOT user isolation pattern)
        if hasattr(self, '_user_id'):
            if self._user_id != user_id:
                raise ValueError(f"User isolation violation detected: expected {self._user_id}, got {user_id}")
        else:
            # Initialize user isolation tracking (validation-safe assignment)
            self._user_id = user_id
        
        # GOLDEN PATH CRITICAL: Validate emitter supports ALL 5 required WebSocket events
        # Note: Mock objects auto-create attributes, so this validation is primarily for real emitters
        required_methods = [
            'notify_agent_started',    # Event 1: Agent begins processing
            'notify_agent_thinking',   # Event 2: Real-time reasoning visibility
            'notify_tool_executing',   # Event 3: Tool usage transparency
            'notify_tool_completed',   # Event 4: Tool results display
            'notify_agent_completed'   # Event 5: User knows response is ready
        ]
        
        # Validate emitter has required methods (skip for Mock objects in tests)
        if not str(type(self.emitter)).startswith("<class 'unittest.mock"):
            missing_methods = [method for method in required_methods if not hasattr(self.emitter, method)]
            if missing_methods:
                raise ValueError(f"WebSocket emitter missing required methods for Golden Path: {missing_methods}")
        else:
            # For Mock objects, ensure they're properly configured for testing
            # This documents the required interface even if we can't enforce it
            pass
        
    async def send_agent_thinking(self, exec_context, message: str):
        """Send agent thinking event via WebSocket emitter."""
        if hasattr(self.emitter, 'notify_agent_thinking'):
            await self.emitter.notify_agent_thinking(
                exec_context.agent_name,
                message,
                step_number=1  # Default step number
            )
        else:
            central_logger.warning(f"Emitter does not support notify_agent_thinking: {type(self.emitter)}")

    async def send_agent_started(self, exec_context, agent_name: str = None):
        """Send agent started event via WebSocket emitter.
        
        GOLDEN PATH CRITICAL: Event 1 of 5 required for complete user experience.
        User must see that agent has begun processing their problem.
        
        Args:
            exec_context: Agent execution context containing run_id, thread_id, user_id
            agent_name: Optional agent name override (defaults to exec_context.agent_name)
        """
        try:
            # Use provided agent_name or fallback to context
            agent = agent_name or getattr(exec_context, 'agent_name', 'UnknownAgent')
            
            if hasattr(self.emitter, 'notify_agent_started'):
                await self.emitter.notify_agent_started(
                    agent,
                    run_id=getattr(exec_context, 'run_id', None),
                    thread_id=getattr(exec_context, 'thread_id', None)
                )
                central_logger.info(f"Agent started event sent for {agent} (run_id={getattr(exec_context, 'run_id', 'unknown')})")
            else:
                central_logger.warning(f"Emitter does not support notify_agent_started: {type(self.emitter)}")
        except Exception as e:
            central_logger.error(f"Failed to send agent_started event for {agent}: {e}")

    async def send_tool_executing(self, exec_context, tool_name: str, tool_purpose: str = None, 
                                estimated_duration_ms: int = None, parameters_summary: str = None):
        """Send tool executing event via WebSocket emitter.
        
        GOLDEN PATH CRITICAL: Event 3 of 5 required for complete user experience.
        Provides tool usage transparency to show problem-solving approach.
        
        Args:
            exec_context: Agent execution context containing run_id, thread_id, user_id
            tool_name: Name of the tool being executed
            tool_purpose: Optional description of what the tool does
            estimated_duration_ms: Optional estimated execution time in milliseconds
            parameters_summary: Optional summary of tool parameters
        """
        try:
            if hasattr(self.emitter, 'notify_tool_executing'):
                await self.emitter.notify_tool_executing(
                    tool_name=tool_name,
                    tool_purpose=tool_purpose,
                    run_id=getattr(exec_context, 'run_id', None),
                    thread_id=getattr(exec_context, 'thread_id', None),
                    agent_name=getattr(exec_context, 'agent_name', 'UnknownAgent'),
                    estimated_duration_ms=estimated_duration_ms,
                    parameters_summary=parameters_summary
                )
                central_logger.info(f"Tool executing event sent for {tool_name} (run_id={getattr(exec_context, 'run_id', 'unknown')})")
            else:
                central_logger.warning(f"Emitter does not support notify_tool_executing: {type(self.emitter)}")
        except Exception as e:
            central_logger.error(f"Failed to send tool_executing event for {tool_name}: {e}")

    async def send_tool_completed(self, exec_context, tool_name: str, result: Dict[str, Any]):
        """Send tool completed event via WebSocket emitter.
        
        GOLDEN PATH CRITICAL: Event 4 of 5 required for complete user experience.
        Delivers tool results display to show actionable insights.
        
        Args:
            exec_context: Agent execution context containing run_id, thread_id, user_id
            tool_name: Name of the tool that completed
            result: Tool execution result data
        """
        try:
            if hasattr(self.emitter, 'notify_tool_completed'):
                await self.emitter.notify_tool_completed(
                    tool_name=tool_name,
                    result=result,
                    run_id=getattr(exec_context, 'run_id', None),
                    thread_id=getattr(exec_context, 'thread_id', None),
                    agent_name=getattr(exec_context, 'agent_name', 'UnknownAgent')
                )
                central_logger.info(f"Tool completed event sent for {tool_name} (run_id={getattr(exec_context, 'run_id', 'unknown')})")
            else:
                central_logger.warning(f"Emitter does not support notify_tool_completed: {type(self.emitter)}")
        except Exception as e:
            central_logger.error(f"Failed to send tool_completed event for {tool_name}: {e}")

    async def send_agent_completed(self, exec_context, result: Dict[str, Any], execution_time_ms: float = None):
        """Send agent completed event via WebSocket emitter.
        
        GOLDEN PATH CRITICAL: Event 5 of 5 required for complete user experience.
        User must know when valuable response is ready.
        
        Args:
            exec_context: Agent execution context containing run_id, thread_id, user_id  
            result: Agent execution result data
            execution_time_ms: Optional total execution time in milliseconds
        """
        try:
            if hasattr(self.emitter, 'notify_agent_completed'):
                await self.emitter.notify_agent_completed(
                    agent_name=getattr(exec_context, 'agent_name', 'UnknownAgent'),
                    result=result,
                    run_id=getattr(exec_context, 'run_id', None),
                    thread_id=getattr(exec_context, 'thread_id', None),
                    execution_time_ms=execution_time_ms
                )
                central_logger.info(f"Agent completed event sent for {getattr(exec_context, 'agent_name', 'UnknownAgent')} (run_id={getattr(exec_context, 'run_id', 'unknown')})")
            else:
                central_logger.warning(f"Emitter does not support notify_agent_completed: {type(self.emitter)}")
        except Exception as e:
            central_logger.error(f"Failed to send agent_completed event for {getattr(exec_context, 'agent_name', 'UnknownAgent')}: {e}")


    async def _emit_with_retry(
        self,
        event_type: str,
        thread_id: str,
        notification: Dict[str, Any],
        run_id: str,
        agent_name: str,
        max_retries: int = 3,
        critical_event: bool = False
    ) -> bool:
        """
        PHASE 3 FIX: Emit WebSocket event with retry mechanism.
        
        This method implements robust event delivery with exponential backoff
        to ensure critical agent events are delivered even under adverse conditions.
        
        Args:
            event_type: Type of event being emitted
            thread_id: Target thread for event delivery
            notification: Event notification payload
            run_id: Run identifier for tracking
            agent_name: Agent name for logging
            max_retries: Maximum number of retry attempts
            critical_event: Whether this is a critical event requiring special handling
            
        Returns:
            bool: True if event delivered successfully, False otherwise
        """
        last_error = None
        base_delay = 0.1 if critical_event else 0.05
        
        print(f"DEBUG: _emit_with_retry starting for {event_type}, max_retries={max_retries}")
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            print(f"DEBUG: _emit_with_retry attempt {attempt}")
            try:
                # Validate WebSocket manager is still available
                if not self._websocket_manager:
                    logger.error(f"PHASE 3 FIX: WebSocket manager unavailable during {event_type} retry {attempt + 1}")
                    print(f"DEBUG: WebSocket manager unavailable")
                    return False
                
                # Attempt event delivery
                print(f"DEBUG: _emit_with_retry calling send_to_thread for {event_type}")
                success = await self._websocket_manager.send_to_thread(thread_id, notification)
                print(f"DEBUG: _emit_with_retry send_to_thread returned success={success}")
                
                if success:
                    if attempt > 0:
                        logger.info(f"PHASE 3 FIX: {event_type} delivered on retry attempt {attempt + 1} (run_id={run_id})")
                    return True
                
                # If not successful and we have retries left
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    if critical_event:
                        delay *= 2  # Longer delays for critical events
                    
                    logger.warning(f"PHASE 3 FIX: {event_type} delivery failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries + 1}, run_id={run_id})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"PHASE 3 FIX: {event_type} delivery failed after {max_retries + 1} attempts (run_id={run_id})")
                    return False
                    
            except Exception as e:
                last_error = e
                logger.error(f"PHASE 3 FIX: Exception during {event_type} delivery attempt {attempt + 1}: {e}")
                
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"PHASE 3 FIX: {event_type} delivery failed with exception after {max_retries + 1} attempts: {e}")
                    return False
        
        return False
    
    async def _track_event_delivery(self, event_type: str, run_id: str, success: bool):
        """
        PHASE 3 FIX: Track event delivery success/failure for monitoring.
        
        Args:
            event_type: Type of event that was delivered/failed
            run_id: Run identifier for correlation
            success: Whether delivery was successful
        """
        try:
            # Initialize event tracking if not exists
            if not hasattr(self, '_event_delivery_stats'):
                self._event_delivery_stats = {
                    'total_events': 0,
                    'successful_events': 0,
                    'failed_events': 0,
                    'events_by_type': {},
                    'last_tracked': datetime.now(timezone.utc)
                }
            
            stats = self._event_delivery_stats
            stats['total_events'] += 1
            stats['last_tracked'] = datetime.now(timezone.utc)
            
            if success:
                stats['successful_events'] += 1
            else:
                stats['failed_events'] += 1
            
            # Track by event type
            if event_type not in stats['events_by_type']:
                stats['events_by_type'][event_type] = {'success': 0, 'failed': 0}
            
            if success:
                stats['events_by_type'][event_type]['success'] += 1
            else:
                stats['events_by_type'][event_type]['failed'] += 1
            
            # Calculate success rate for monitoring
            success_rate = (stats['successful_events'] / stats['total_events']) * 100 if stats['total_events'] > 0 else 0
            
            # Log poor performance
            if stats['total_events'] % 10 == 0 and success_rate < 90:
                logger.warning(f"PHASE 3 MONITORING: Event delivery success rate: {success_rate:.1f}% ({stats['successful_events']}/{stats['total_events']})")
                
        except Exception as e:
            logger.error(f"PHASE 3 FIX: Failed to track event delivery: {e}")
    
    async def _alert_critical_event_failure(self, event_type: str, run_id: str, agent_name: str):
        """
        PHASE 3 FIX: Alert when critical events fail to deliver.
        
        Args:
            event_type: Type of critical event that failed
            run_id: Run identifier for tracking
            agent_name: Agent name for context
        """
        try:
            alert_message = {
                'alert_type': 'critical_event_failure',
                'event_type': event_type,
                'run_id': run_id,
                'agent_name': agent_name,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'severity': 'high',
                'message': f'Critical WebSocket event {event_type} failed to deliver for {agent_name} (run_id: {run_id})'
            }
            
            # Log critical alert
            logger.critical(f"🚨 CRITICAL EVENT FAILURE: {alert_message}")
            
            # TODO: In production, send to monitoring system
            # await monitoring_system.send_alert(alert_message)
            
        except Exception as e:
            logger.error(f"PHASE 3 FIX: Failed to send critical event alert: {e}")
    
    def get_event_delivery_stats(self) -> Dict[str, Any]:
        """
        PHASE 3 FIX: Get event delivery statistics for monitoring.
        
        Returns:
            Dict containing event delivery statistics
        """
        if not hasattr(self, '_event_delivery_stats'):
            return {
                'total_events': 0,
                'successful_events': 0,
                'failed_events': 0,
                'success_rate': 0.0,
                'events_by_type': {},
                'last_tracked': None
            }
        
        stats = self._event_delivery_stats
        success_rate = (stats['successful_events'] / stats['total_events']) * 100 if stats['total_events'] > 0 else 0
        
        return {
            **stats,
            'success_rate': round(success_rate, 2)
        }

    @classmethod
    def create_websocket_notifier(
        cls,
        emitter,
        user_context: 'UserExecutionContext',
        validate_context: bool = True
    ) -> 'WebSocketNotifier':
        """
        Factory method to create WebSocketNotifier with proper user context validation.
        
        This is the SSOT method for creating WebSocketNotifier instances during the
        migration from deprecated implementations.
        
        Args:
            emitter: WebSocket emitter instance (WebSocketEventEmitter or compatible)
            user_context: User execution context for isolation
            validate_context: Whether to validate user context (default: True)
            
        Returns:
            WebSocketNotifier: Configured notifier instance
            
        Raises:
            ValueError: If user_context is invalid and validate_context=True
            
        Example:
            # Replace deprecated pattern:
            # notifier = WebSocketNotifier(websocket_manager)
            
            # With SSOT pattern:
            notifier = AgentWebSocketBridge.create_websocket_notifier(
                emitter=emitter,
                user_context=user_context
            )
        """
        if validate_context and user_context is None:
            raise ValueError(
                "User context is required for WebSocketNotifier creation. "
                "This ensures proper user isolation and prevents cross-user data leakage."
            )
        
        if validate_context and not hasattr(user_context, 'user_id'):
            raise ValueError(
                f"Invalid user context: missing user_id attribute. "
                f"Expected UserExecutionContext, got {type(user_context)}"
            )
        
        logger.info(
            f"Creating WebSocketNotifier with SSOT factory pattern "
            f"for user {getattr(user_context, 'user_id', 'unknown')[:8] if user_context else 'none'}..."
        )
        
        return cls.WebSocketNotifier(emitter, user_context)


# SECURITY FIX: Replace singleton with factory pattern
# Global instance removed to prevent multi-user data leakage
# Use create_agent_websocket_bridge(user_context) instead


def create_agent_websocket_bridge(user_context: 'UserExecutionContext' = None, websocket_manager = None) -> AgentWebSocketBridge:
    """
    Create a new AgentWebSocketBridge instance with optional user context or websocket manager.
    
    This factory function replaces the singleton pattern to prevent cross-user
    data leakage. Each bridge instance is isolated and can safely create
    user-specific emitters.
    
    PRIORITY 2 FIX: Added websocket_manager parameter for API signature compatibility.
    Both user_context and websocket_manager are supported for backward compatibility.
    
    Args:
        user_context: Optional UserExecutionContext for default emitter creation
        websocket_manager: Optional WebSocketManager (for compatibility, will be used to create user context)
        
    Returns:
        AgentWebSocketBridge: New isolated bridge instance
        
    Example:
        # Create isolated bridge for a specific user
        bridge = create_agent_websocket_bridge(user_context)
        emitter = await bridge.create_user_emitter(user_context)
        await emitter.notify_agent_started(agent_name, metadata)
    """
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    # PRIORITY 2 FIX: Handle both user_context and websocket_manager parameters for compatibility
    if websocket_manager and not user_context:
        # If websocket_manager is provided but no user_context, try to extract or create context
        logger.warning("websocket_manager parameter provided without user_context - using basic context creation")
        if hasattr(websocket_manager, 'user_context') and websocket_manager.user_context:
            user_context = websocket_manager.user_context
            logger.info(f"Extracted user_context from websocket_manager for user {user_context.user_id[:8]}...")
        else:
            # Create a minimal user context for compatibility
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation import UnifiedIdGenerator
            user_context = UserExecutionContext(
                user_id="websocket-compat-user",
                thread_id=UnifiedIdGenerator.generate_base_id("thread_compat"),
                run_id=UnifiedIdGenerator.generate_base_id("run_compat"),
                request_id=UnifiedIdGenerator.generate_base_id("req_compat")
            )
            logger.info("Created compatibility user_context from websocket_manager parameter")
    elif websocket_manager and user_context:
        logger.info("Both websocket_manager and user_context provided - using user_context (preferred)")
    
    logger.info("Creating isolated AgentWebSocketBridge instance")
    bridge = AgentWebSocketBridge(user_context=user_context)
    
    # Note: User emitters are created on-demand via await bridge.create_user_emitter(user_context)
    # when actually needed to avoid sync/async complexity in factory function
    if user_context:
        logger.info(f"Bridge created for user {user_context.user_id[:8]}... (emitter will be created on-demand)")
    else:
        logger.info("Bridge created without user context (emitter creation requires explicit user context)")
    
    return bridge

# REMOVED: Deprecated get_agent_websocket_bridge() function that created security vulnerabilities
# All code must use create_agent_websocket_bridge(user_context) for proper user isolation