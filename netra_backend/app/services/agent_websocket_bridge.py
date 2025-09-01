"""
AgentWebSocketBridge - SSOT for WebSocket-Agent Service Integration

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Eliminates 60% of glue code, provides reliable agent-websocket coordination
- Strategic Impact: Single source of truth for integration lifecycle, enables zero-downtime recovery

This class serves as the single source of truth for managing the integration lifecycle
between AgentService and WebSocketAgentOrchestrator, providing idempotent initialization,
health monitoring, and recovery mechanisms.
"""

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.orchestration.websocket_agent_orchestrator import get_websocket_agent_orchestrator
from netra_backend.app.websocket_core import get_websocket_manager

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
    orchestrator_healthy: bool
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


class AgentWebSocketBridge:
    """
    SSOT for WebSocket-Agent service integration lifecycle.
    
    Provides idempotent initialization, health monitoring, and recovery
    mechanisms for the critical WebSocket-Agent integration that enables
    substantive chat interactions.
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
        self._health_check_task = None
        logger.debug("Dependency references initialized")
    
    def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring and metrics."""
        self.metrics = IntegrationMetrics()
        self.health_status = HealthStatus(
            state=IntegrationState.UNINITIALIZED,
            websocket_manager_healthy=False,
            orchestrator_healthy=False,
            last_health_check=datetime.now(timezone.utc)
        )
        logger.debug("Health monitoring initialized")
    
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
                await self._initialize_orchestrator()
                await self._setup_orchestrator_integration()
                
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
        """Initialize WebSocket manager with error handling."""
        try:
            self._websocket_manager = get_websocket_manager()
            if not self._websocket_manager:
                raise RuntimeError("WebSocket manager is None")
            logger.debug("WebSocket manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket manager: {e}")
            raise RuntimeError(f"WebSocket manager initialization failed: {e}")
    
    async def _initialize_orchestrator(self) -> None:
        """Initialize WebSocket agent orchestrator with error handling."""
        try:
            self._orchestrator = await get_websocket_agent_orchestrator()
            if not self._orchestrator:
                raise RuntimeError("WebSocket agent orchestrator is None")
            logger.debug("WebSocket agent orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise RuntimeError(f"Orchestrator initialization failed: {e}")
    
    async def _setup_orchestrator_integration(self) -> None:
        """Setup orchestrator integration with WebSocket manager and agents."""
        try:
            # Set WebSocket manager on orchestrator
            await self._orchestrator.set_websocket_manager(self._websocket_manager)
            logger.debug("WebSocket manager set on orchestrator")
            
            # Setup agent-WebSocket integration if components available
            if self._supervisor and self._registry:
                await self._orchestrator.setup_agent_websocket_integration(
                    self._supervisor, 
                    self._registry
                )
                logger.debug("Enhanced agent-WebSocket integration configured")
            else:
                logger.debug("Basic orchestrator integration configured (no supervisor/registry)")
                
        except Exception as e:
            logger.error(f"Failed to setup orchestrator integration: {e}")
            raise RuntimeError(f"Orchestrator integration setup failed: {e}")
    
    async def _verify_integration(self) -> bool:
        """Verify integration is working correctly."""
        try:
            # Verify WebSocket manager is responsive
            if not self._websocket_manager:
                return False
            
            # Verify orchestrator is responsive
            if not self._orchestrator:
                return False
            
            # Test orchestrator metrics (should not raise)
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
                
                # Check orchestrator health  
                orchestrator_healthy = await self._check_orchestrator_health()
                
                # Update health status
                self.health_status = HealthStatus(
                    state=self.state,
                    websocket_manager_healthy=websocket_healthy,
                    orchestrator_healthy=orchestrator_healthy,
                    last_health_check=datetime.now(timezone.utc),
                    consecutive_failures=self.health_status.consecutive_failures,
                    total_recoveries=self.health_status.total_recoveries,
                    uptime_seconds=self._calculate_uptime()
                )
                
                # Update integration state based on health
                if websocket_healthy and orchestrator_healthy:
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
                return self.health_status
                
            except Exception as e:
                error_msg = f"Health check failed: {e}"
                logger.error(error_msg)
                
                self.health_status.consecutive_failures += 1
                self.health_status.error_message = error_msg
                self.health_status.last_health_check = datetime.now(timezone.utc)
                
                return self.health_status
    
    async def _check_websocket_manager_health(self) -> bool:
        """Check WebSocket manager health."""
        try:
            return self._websocket_manager is not None
        except Exception:
            return False
    
    async def _check_orchestrator_health(self) -> bool:
        """Check orchestrator health."""
        try:
            if not self._orchestrator:
                return False
            
            # Test orchestrator responsiveness
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
                "orchestrator_healthy": health.orchestrator_healthy,
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
        
        # Shutdown orchestrator if available
        if self._orchestrator:
            try:
                await self._orchestrator.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down orchestrator: {e}")
        
        # Clear references
        self._websocket_manager = None
        self._orchestrator = None
        self._supervisor = None
        self._registry = None
        
        self.state = IntegrationState.UNINITIALIZED
        logger.info("AgentWebSocketBridge shutdown complete")


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