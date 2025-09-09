"""
GCP Cloud Run WebSocket Initialization Validator - SSOT Implementation

MISSION CRITICAL: Prevents 1011 WebSocket errors in GCP Cloud Run by ensuring 
agent_supervisor service readiness before accepting WebSocket connections.

ROOT CAUSE FIX: GCP Cloud Run accepts WebSocket connections before backend services 
are ready, causing connection failures. This module provides GCP-optimized readiness 
validation using existing SSOT patterns.

SSOT COMPLIANCE:
- Uses shared.isolated_environment for environment detection  
- Integrates with existing deterministic startup sequence (smd.py)
- Uses unified WebSocket infrastructure from websocket_core
- Follows shared.lifecycle patterns for service management

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery  
- Value Impact: Eliminates 1011 WebSocket errors preventing chat functionality
- Strategic Impact: Enables reliable WebSocket connections in production GCP environment
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


class GCPReadinessState(Enum):
    """GCP service readiness states for WebSocket initialization."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing" 
    DEPENDENCIES_READY = "dependencies_ready"
    SERVICES_READY = "services_ready"
    WEBSOCKET_READY = "websocket_ready"
    FAILED = "failed"


@dataclass
class ServiceReadinessCheck:
    """Configuration for service readiness validation."""
    name: str
    validator: Callable[[], bool]
    timeout_seconds: float = 30.0
    retry_count: int = 5
    retry_delay: float = 1.0
    is_critical: bool = True
    description: str = ""


@dataclass 
class GCPReadinessResult:
    """Result of GCP readiness validation."""
    ready: bool
    state: GCPReadinessState
    elapsed_time: float
    failed_services: list[str]
    warnings: list[str]
    details: Dict[str, Any]


class GCPWebSocketInitializationValidator:
    """
    GCP-optimized WebSocket initialization validator using SSOT patterns.
    
    CRITICAL: This class prevents 1011 WebSocket errors by validating that
    all critical services are ready before GCP Cloud Run routes WebSocket connections.
    
    SSOT INTEGRATION:
    - Uses shared.isolated_environment for environment detection
    - Integrates with smd.py deterministic startup phases
    - Uses existing WebSocket infrastructure from websocket_core
    """
    
    def __init__(self, app_state: Optional[Any] = None):
        self.app_state = app_state
        self.logger = central_logger.get_logger(__name__)
        self.env_manager = get_env()
        
        # GCP-specific configuration
        self.environment = self.env_manager.get('ENVIRONMENT', '').lower()
        self.is_gcp_environment = self.environment in ['staging', 'production']
        self.is_cloud_run = self.env_manager.get('K_SERVICE') is not None
        
        # Readiness tracking
        self.current_state = GCPReadinessState.UNKNOWN
        self.readiness_checks: Dict[str, ServiceReadinessCheck] = {}
        self.validation_start_time = 0.0
        
        self._register_critical_service_checks()
    
    def update_environment_configuration(self, environment: str, is_gcp: bool) -> None:
        """
        Update environment configuration and re-register service checks.
        
        CRITICAL: This method allows tests to properly override environment detection
        and ensures service checks use the correct timeouts and configurations.
        
        Args:
            environment: Environment name (e.g., 'staging', 'production', 'test')
            is_gcp: Whether this is a GCP environment
        """
        self.environment = environment.lower()
        self.is_gcp_environment = is_gcp
        
        # Re-register service checks with updated environment configuration
        self.readiness_checks.clear()
        self._register_critical_service_checks()
        
        self.logger.debug(
            f"Environment configuration updated: environment={self.environment}, "
            f"is_gcp={self.is_gcp_environment}, Redis timeout={self.readiness_checks['redis'].timeout_seconds}s"
        )
    
    def _register_critical_service_checks(self) -> None:
        """Register critical service readiness checks using SSOT patterns."""
        
        # Phase 2-3 Dependencies: Database, Redis, Auth
        self.readiness_checks['database'] = ServiceReadinessCheck(
            name='database',
            validator=self._validate_database_readiness,
            timeout_seconds=45.0 if self.is_gcp_environment else 15.0,
            retry_count=8 if self.is_gcp_environment else 3,
            retry_delay=2.0 if self.is_gcp_environment else 1.0,
            is_critical=True,
            description="Database session factory and connectivity"
        )
        
        self.readiness_checks['redis'] = ServiceReadinessCheck(
            name='redis',
            validator=self._validate_redis_readiness,
            timeout_seconds=60.0 if self.is_gcp_environment else 10.0,  # BUGFIX: Increased from 30.0 to 60.0 for staging race condition fix
            retry_count=5,
            retry_delay=1.5 if self.is_gcp_environment else 1.0,
            is_critical=True,
            description="Redis connection and caching system"
        )
        
        self.readiness_checks['auth_validation'] = ServiceReadinessCheck(
            name='auth_validation',
            validator=self._validate_auth_system_readiness,
            timeout_seconds=20.0,
            retry_count=3,
            retry_delay=1.0,
            is_critical=True,
            description="Auth validation and JWT system"
        )
        
        # Phase 5: Critical Services - Agent Supervisor & WebSocket Bridge
        self.readiness_checks['agent_supervisor'] = ServiceReadinessCheck(
            name='agent_supervisor',
            validator=self._validate_agent_supervisor_readiness,
            timeout_seconds=60.0 if self.is_gcp_environment else 30.0,
            retry_count=10 if self.is_gcp_environment else 5,
            retry_delay=2.0 if self.is_gcp_environment else 1.0,
            is_critical=True,
            description="Agent supervisor and chat pipeline"
        )
        
        self.readiness_checks['websocket_bridge'] = ServiceReadinessCheck(
            name='websocket_bridge',
            validator=self._validate_websocket_bridge_readiness,
            timeout_seconds=30.0,
            retry_count=5,
            retry_delay=1.0,
            is_critical=True,
            description="AgentWebSocketBridge for real-time events"
        )
        
        # Phase 6: WebSocket Integration
        self.readiness_checks['websocket_integration'] = ServiceReadinessCheck(
            name='websocket_integration',
            validator=self._validate_websocket_integration_readiness,
            timeout_seconds=20.0,
            retry_count=3,
            retry_delay=1.0,
            is_critical=True,
            description="Complete WebSocket integration and event delivery"
        )
    
    def _validate_database_readiness(self) -> bool:
        """Validate database readiness using SSOT patterns."""
        try:
            if not self.app_state:
                return False
            
            # Check db_session_factory exists and is not None
            if not hasattr(self.app_state, 'db_session_factory'):
                return False
            
            db_factory = self.app_state.db_session_factory
            if db_factory is None:
                return False
            
            # For GCP Cloud SQL, also check database_available flag  
            if hasattr(self.app_state, 'database_available'):
                return bool(self.app_state.database_available)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Database readiness check failed: {e}")
            return False
    
    def _validate_redis_readiness(self) -> bool:
        """Validate Redis readiness using SSOT patterns with race condition fix.
        
        CRITICAL FIX: This method is now synchronous to properly work with ServiceReadinessCheck.
        The grace period is applied synchronously using time.sleep() instead of asyncio.sleep().
        This ensures the grace period is measurable and works in all contexts.
        """
        try:
            if not self.app_state:
                return False
            
            if not hasattr(self.app_state, 'redis_manager'):
                return False
            
            redis_manager = self.app_state.redis_manager
            if redis_manager is None:
                return False
            
            # Additional check: try to verify redis manager is initialized
            if hasattr(redis_manager, 'is_connected'):
                is_connected = redis_manager.is_connected()
                
                # BUGFIX: Grace period for background task stabilization
                # If connected but in GCP environment, add small delay to allow
                # background monitoring tasks to fully stabilize (race condition fix)
                if is_connected and self.is_gcp_environment:
                    # CRITICAL FIX: Use synchronous sleep for measurable grace period
                    # This prevents async/await issues and makes the grace period testable
                    time.sleep(0.5)  # 500ms grace period for background task stability
                
                return is_connected
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Redis readiness check failed: {e}")
            return False
    
    def _validate_auth_system_readiness(self) -> bool:
        """Validate auth system readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check for auth validation completion flag
            if hasattr(self.app_state, 'auth_validation_complete'):
                return bool(self.app_state.auth_validation_complete)
            
            # Check for key manager (critical for auth)
            if not hasattr(self.app_state, 'key_manager'):
                return False
            
            return self.app_state.key_manager is not None
            
        except Exception as e:
            self.logger.debug(f"Auth system readiness check failed: {e}")
            return False
    
    def _validate_agent_supervisor_readiness(self) -> bool:
        """Validate agent supervisor readiness - CRITICAL for chat."""
        try:
            if not self.app_state:
                return False
            
            # Check agent_supervisor exists and is not None
            if not hasattr(self.app_state, 'agent_supervisor'):
                return False
            
            agent_supervisor = self.app_state.agent_supervisor
            if agent_supervisor is None:
                return False
            
            # Check thread_service (required for chat functionality)
            if not hasattr(self.app_state, 'thread_service'):
                return False
            
            if self.app_state.thread_service is None:
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Agent supervisor readiness check failed: {e}")
            return False
    
    def _validate_websocket_bridge_readiness(self) -> bool:
        """Validate AgentWebSocketBridge readiness using SSOT patterns."""
        try:
            if not self.app_state:
                return False
            
            # Check agent_websocket_bridge exists and is not None
            if not hasattr(self.app_state, 'agent_websocket_bridge'):
                return False
            
            bridge = self.app_state.agent_websocket_bridge
            if bridge is None:
                return False
            
            # Check bridge has critical notification methods
            required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
            for method in required_methods:
                if not hasattr(bridge, method):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"WebSocket bridge readiness check failed: {e}")
            return False
    
    def _validate_websocket_integration_readiness(self) -> bool:
        """Validate complete WebSocket integration readiness."""
        try:
            if not self.app_state:
                return False
            
            # Check startup completion flag from deterministic startup
            if hasattr(self.app_state, 'startup_complete'):
                startup_complete = bool(self.app_state.startup_complete)
                if not startup_complete:
                    return False
            
            # Check that we're not in a failed startup state
            if hasattr(self.app_state, 'startup_failed'):
                if bool(self.app_state.startup_failed):
                    return False
            
            # Verify Phase 6 (WEBSOCKET) completion
            if hasattr(self.app_state, 'startup_phase'):
                current_phase = str(self.app_state.startup_phase)
                # Phase should be "complete" or "finalize"
                if current_phase in ['init', 'dependencies', 'database', 'cache', 'services', 'websocket']:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"WebSocket integration readiness check failed: {e}")
            return False
    
    async def validate_gcp_readiness_for_websocket(
        self, 
        timeout_seconds: float = 120.0
    ) -> GCPReadinessResult:
        """
        Validate GCP readiness for WebSocket connections.
        
        CRITICAL: This method prevents 1011 WebSocket errors by ensuring all
        required services are ready before GCP routes WebSocket connections.
        
        Args:
            timeout_seconds: Maximum time to wait for readiness
            
        Returns:
            GCPReadinessResult with validation status and details
        """
        self.validation_start_time = time.time()
        failed_services = []
        warnings = []
        details = {}
        
        self.logger.info(f"🔍 GCP WebSocket readiness validation started (timeout: {timeout_seconds}s)")
        
        try:
            # Skip validation for non-GCP environments
            if not self.is_gcp_environment:
                self.logger.info("Non-GCP environment detected - skipping GCP-specific validation")
                return GCPReadinessResult(
                    ready=True,
                    state=GCPReadinessState.WEBSOCKET_READY,
                    elapsed_time=time.time() - self.validation_start_time,
                    failed_services=[],
                    warnings=["Skipped GCP validation for non-GCP environment"],
                    details={"environment": self.environment, "gcp_detected": False}
                )
            
            self.current_state = GCPReadinessState.INITIALIZING
            
            # Phase 1: Validate Dependencies (Database, Redis, Auth)
            self.logger.info("📋 Phase 1: Validating dependencies (Database, Redis, Auth)...")
            dependencies_ready = await self._validate_service_group([
                'database', 'redis', 'auth_validation'
            ], timeout_seconds=60.0)
            
            if not dependencies_ready['success']:
                failed_services.extend(dependencies_ready['failed'])
                self.current_state = GCPReadinessState.FAILED
            else:
                self.current_state = GCPReadinessState.DEPENDENCIES_READY
                self.logger.info("✅ Phase 1 Complete: Dependencies ready")
            
            # Phase 2: Validate Services (Agent Supervisor, WebSocket Bridge)
            if self.current_state != GCPReadinessState.FAILED:
                self.logger.info("📋 Phase 2: Validating services (Agent Supervisor, WebSocket Bridge)...")
                services_ready = await self._validate_service_group([
                    'agent_supervisor', 'websocket_bridge'
                ], timeout_seconds=60.0)
                
                if not services_ready['success']:
                    failed_services.extend(services_ready['failed'])
                    self.current_state = GCPReadinessState.FAILED
                else:
                    self.current_state = GCPReadinessState.SERVICES_READY
                    self.logger.info("✅ Phase 2 Complete: Services ready")
            
            # Phase 3: Validate WebSocket Integration
            if self.current_state == GCPReadinessState.SERVICES_READY:
                self.logger.info("📋 Phase 3: Validating WebSocket integration...")
                integration_ready = await self._validate_service_group([
                    'websocket_integration'
                ], timeout_seconds=30.0)
                
                if not integration_ready['success']:
                    failed_services.extend(integration_ready['failed'])
                    self.current_state = GCPReadinessState.FAILED
                else:
                    self.current_state = GCPReadinessState.WEBSOCKET_READY
                    self.logger.info("✅ Phase 3 Complete: WebSocket integration ready")
            
            # Build result
            elapsed_time = time.time() - self.validation_start_time
            ready = self.current_state == GCPReadinessState.WEBSOCKET_READY
            
            details = {
                "environment": self.environment,
                "is_cloud_run": self.is_cloud_run,
                "gcp_detected": self.is_gcp_environment,
                "validation_phases_completed": self.current_state.value,
                "total_checks": len(self.readiness_checks),
                "failed_check_count": len(failed_services)
            }
            
            if ready:
                self.logger.info(f"🟢 GCP WebSocket readiness validation SUCCESS ({elapsed_time:.2f}s)")
                self.logger.info("   All critical services ready - WebSocket connections can be accepted")
            else:
                self.logger.error(f"🔴 GCP WebSocket readiness validation FAILED ({elapsed_time:.2f}s)")
                self.logger.error(f"   Failed services: {', '.join(failed_services)}")
                self.logger.error("   WebSocket connections should be rejected to prevent 1011 errors")
            
            return GCPReadinessResult(
                ready=ready,
                state=self.current_state,
                elapsed_time=elapsed_time,
                failed_services=failed_services,
                warnings=warnings,
                details=details
            )
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - self.validation_start_time
            self.logger.error(f"🔴 GCP WebSocket readiness validation TIMEOUT ({elapsed_time:.2f}s)")
            self.current_state = GCPReadinessState.FAILED
            
            return GCPReadinessResult(
                ready=False,
                state=GCPReadinessState.FAILED,
                elapsed_time=elapsed_time,
                failed_services=failed_services + ["timeout"],
                warnings=warnings + [f"Validation timeout after {timeout_seconds}s"],
                details={"timeout": True}
            )
            
        except Exception as e:
            elapsed_time = time.time() - self.validation_start_time
            self.logger.error(f"🔴 GCP WebSocket readiness validation ERROR: {e} ({elapsed_time:.2f}s)")
            self.current_state = GCPReadinessState.FAILED
            
            return GCPReadinessResult(
                ready=False,
                state=GCPReadinessState.FAILED,
                elapsed_time=elapsed_time,
                failed_services=failed_services + ["validation_error"],
                warnings=warnings + [f"Validation error: {str(e)}"],
                details={"error": str(e)}
            )
    
    async def _validate_service_group(
        self, 
        service_names: list[str], 
        timeout_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """Validate a group of services with timeout and retry logic."""
        failed = []
        success_count = 0
        
        for service_name in service_names:
            if service_name not in self.readiness_checks:
                self.logger.warning(f"Service check not found: {service_name}")
                failed.append(service_name)
                continue
            
            check = self.readiness_checks[service_name]
            service_ready = await self._validate_single_service(check, timeout_seconds)
            
            if service_ready:
                success_count += 1
                self.logger.info(f"   ✅ {service_name}: Ready ({check.description})")
            else:
                if check.is_critical:
                    failed.append(service_name)
                    self.logger.error(f"   ❌ {service_name}: Failed ({check.description})")
                else:
                    self.logger.warning(f"   ⚠️  {service_name}: Failed (non-critical)")
        
        return {
            "success": len(failed) == 0,
            "failed": failed,
            "success_count": success_count,
            "total_count": len(service_names)
        }
    
    async def _validate_single_service(
        self, 
        check: ServiceReadinessCheck, 
        timeout_seconds: float
    ) -> bool:
        """Validate a single service with retry logic."""
        start_time = time.time()
        
        for attempt in range(check.retry_count + 1):
            try:
                # Check if validator is async
                if asyncio.iscoroutinefunction(check.validator):
                    result = await check.validator()
                else:
                    result = check.validator()
                
                if result:
                    return True
                
                # If not ready and we have more retries, wait
                if attempt < check.retry_count:
                    await asyncio.sleep(check.retry_delay)
                
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Service check exception for {check.name}: {e}")
                if attempt < check.retry_count:
                    await asyncio.sleep(check.retry_delay)
        
        return False


# SSOT Factory Function
def create_gcp_websocket_validator(app_state: Optional[Any] = None) -> GCPWebSocketInitializationValidator:
    """
    Create GCP WebSocket initialization validator using SSOT patterns.
    
    SSOT COMPLIANCE: This is the canonical way to create validators.
    All other creation methods should delegate to this function.
    """
    return GCPWebSocketInitializationValidator(app_state)


# Integration with existing startup sequence  
@asynccontextmanager
async def gcp_websocket_readiness_guard(app_state: Any, timeout: float = 120.0):
    """
    Context manager for GCP WebSocket readiness validation.
    
    INTEGRATION: Use this in WebSocket route handlers to prevent 1011 errors.
    
    Usage:
        async with gcp_websocket_readiness_guard(app.state):
            # WebSocket connection is safe to accept
            await websocket.accept()
    """
    validator = create_gcp_websocket_validator(app_state)
    
    try:
        # Validate readiness before yielding
        result = await validator.validate_gcp_readiness_for_websocket(timeout)
        
        if not result.ready:
            raise RuntimeError(
                f"GCP WebSocket readiness validation failed. "
                f"Failed services: {', '.join(result.failed_services)}. "
                f"Rejecting WebSocket connection to prevent 1011 errors."
            )
        
        # Yield control - WebSocket connection is safe
        yield result
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"GCP WebSocket readiness guard error: {e}")
        raise


# Health check endpoint integration
async def gcp_websocket_readiness_check(app_state: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Health check function for GCP WebSocket readiness.
    
    INTEGRATION: Use this in /health endpoints to report WebSocket readiness.
    
    Returns:
        Tuple of (ready: bool, details: dict)
    """
    validator = create_gcp_websocket_validator(app_state)
    result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=30.0)
    
    return result.ready, {
        "websocket_ready": result.ready,
        "state": result.state.value,
        "elapsed_time": result.elapsed_time,
        "failed_services": result.failed_services,
        "warnings": result.warnings,
        "gcp_environment": validator.is_gcp_environment,
        "cloud_run": validator.is_cloud_run
    }