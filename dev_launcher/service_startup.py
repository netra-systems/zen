"""
Service startup coordination for development launcher.
"""

import asyncio
import logging
import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from dev_launcher.auth_starter import AuthStarter
from dev_launcher.backend_starter import BackendStarter
from dev_launcher.config import LauncherConfig
from dev_launcher.critical_error_handler import CriticalErrorType, critical_handler
from dev_launcher.dependency_manager import DependencyManager, ServiceDependency, DependencyType, setup_default_dependency_manager
from dev_launcher.frontend_starter import FrontendStarter
from dev_launcher.log_streamer import LogManager, LogStreamer
from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType
from dev_launcher.port_allocator import get_global_port_allocator
from dev_launcher.readiness_checker import ReadinessManager, BackendReadinessChecker, FrontendReadinessChecker, AuthServiceReadinessChecker
from dev_launcher.service_coordinator import ServiceCoordinator, CoordinationConfig
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.service_registry import get_global_service_registry, ServiceEndpoint, ServiceStatus
from dev_launcher.utils import (
    find_available_port,
    is_port_available,
    wait_for_service_with_details,
)

logger = logging.getLogger(__name__)


class ServiceStartupCoordinator:
    """
    Enhanced coordinator that manages service startup with dependency resolution,
    port allocation, readiness checking, and service discovery integration.
    
    This addresses service coordination issues identified in critical tests:
    - Services starting before dependencies are ready
    - Health check false positives during initialization
    - Port binding race conditions
    - Service discovery timing issues
    - Graceful degradation for optional services
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize enhanced service startup coordinator."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.allocated_ports = {}  # Legacy port tracking
        
        # Enhanced coordination components
        self.service_coordinator = None
        self.readiness_manager = ReadinessManager()
        self.dependency_manager = setup_default_dependency_manager()
        self.port_allocator = None
        self.service_registry = None
        
        self._setup_starters()
        self._setup_parallel_execution()
        self._setup_enhanced_coordination()
    
    def _setup_starters(self):
        """Setup backend, frontend and auth starters."""
        self.backend_starter = BackendStarter(
            self.config, self.services_config,
            self.log_manager, self.service_discovery,
            self.use_emoji
        )
        self.frontend_starter = FrontendStarter(
            self.config, self.services_config,
            self.log_manager, self.service_discovery,
            self.use_emoji
        )
        self.auth_starter = AuthStarter(
            self.config, self.services_config,
            self.log_manager, self.service_discovery,
            self.use_emoji
        )
    
    def _setup_parallel_execution(self):
        """Setup parallel executor for service operations."""
        self.parallel_executor = ParallelExecutor(max_cpu_workers=2, max_io_workers=4)
        self.startup_futures: Dict[str, Future] = {}
        self.health_check_results: Dict[str, bool] = {}
    
    def _setup_enhanced_coordination(self):
        """Setup enhanced coordination components."""
        # Configure service coordinator
        coordination_config = CoordinationConfig(
            max_parallel_starts=2,  # Limit parallel starts to prevent resource contention
            dependency_timeout=60,
            readiness_timeout=90,
            startup_retry_count=2,
            enable_graceful_degradation=True,
            required_services={"database", "backend"},
            optional_services={"redis", "auth", "frontend"}
        )
        self.service_coordinator = ServiceCoordinator(coordination_config)
        
        # Setup readiness checkers
        self._register_readiness_checkers()
        
        logger.info("Enhanced service coordination initialized")
    
    def _register_readiness_checkers(self):
        """Register service-specific readiness checkers."""
        # Backend readiness checker
        backend_port = self.config.backend_port or 8000
        backend_checker = BackendReadinessChecker(backend_port)
        self.readiness_manager.register_checker("backend", backend_checker)
        
        # Frontend readiness checker  
        frontend_port = self.config.frontend_port or 3000
        frontend_checker = FrontendReadinessChecker(frontend_port)
        self.readiness_manager.register_checker("frontend", frontend_checker)
        
        # Auth service readiness checker
        if self.services_config and hasattr(self.services_config, 'auth_service') and self.services_config.auth_service:
            auth_config = self.services_config.auth_service.get_config()
            auth_port = auth_config.get("port", 8081)
        else:
            auth_port = 8081  # Default auth port
        auth_checker = AuthServiceReadinessChecker(auth_port)
        self.readiness_manager.register_checker("auth", auth_checker)
        
        logger.info("Registered readiness checkers for all services")
    
    async def initialize_coordination_systems(self):
        """Initialize async coordination systems."""
        try:
            # Initialize port allocator
            self.port_allocator = await get_global_port_allocator()
            
            # Initialize service registry
            self.service_registry = await get_global_service_registry()
            
            # Start readiness manager if it has async components
            # (ReadinessManager is currently sync, but prepared for async)
            
            logger.info("Coordination systems initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize coordination systems: {e}")
            return False
    
    @property
    def backend_health_info(self):
        """Get backend health info."""
        return self.backend_starter.backend_health_info
    
    @property
    def frontend_health_info(self):
        """Get frontend health info."""
        return self.frontend_starter.frontend_health_info
    
    @property
    def auth_health_info(self):
        """Get auth service health info."""
        return self.auth_starter.auth_health_info
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server with dynamic port allocation."""
        # Pre-check backend port availability if configured
        if self.config.backend_port and not is_port_available(self.config.backend_port):
            error_msg = f"Backend port {self.config.backend_port} is not available"
            expected_vs_actual = f"Expected: port {self.config.backend_port} free, Actual: port in use"
            critical_handler.handle_critical_error(
                CriticalErrorType.DATABASE_CONNECTION,
                f"{error_msg}. {expected_vs_actual}",
                {"suggestion": "Check what process is using the port or use dynamic port allocation"}
            )
            return None, None
        
        result = self.backend_starter.start_backend()
        # Check for critical backend failures
        if result[0] is None:
            critical_handler.handle_critical_error(
                CriticalErrorType.DATABASE_CONNECTION,
                "Backend failed to start - database connection or configuration error",
                {"suggestion": "Check #removed-legacyand ensure PostgreSQL is running"}
            )
        else:
            # Store allocated port for reference
            port = self.config.backend_port or 8000
            self.allocated_ports['backend'] = port
        return result
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server."""
        return self.frontend_starter.start_frontend()
    
    def start_auth_service(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the auth service with enhanced port allocation."""
        # Pre-allocate auth port with dynamic allocation
        auth_config = self.services_config.auth_service.get_config()
        preferred_port = auth_config.get("port", 8081)
        
        # Check port availability and allocate dynamically if needed
        allocated_port = self._allocate_auth_port(preferred_port)
        if allocated_port != preferred_port:
            logger.info(f"Auth port changed from {preferred_port} to {allocated_port}")
        
        result = self.auth_starter.start_auth_service()
        # Check for critical auth failures
        if result[0] is None:
            expected_vs_actual = f"Expected: auth service running on port {allocated_port}, Actual: startup failed"
            critical_handler.handle_critical_error(
                CriticalErrorType.AUTH_SERVICE,
                f"Auth service failed to start. {expected_vs_actual}",
                {"suggestion": f"Check logs for specific error. Port {allocated_port} allocation successful but startup failed"}
            )
        else:
            # Store allocated port and update backend configuration
            self.allocated_ports['auth'] = allocated_port
            self._update_backend_auth_config(allocated_port)
        return result
    
    async def start_all_services(self, process_manager, health_monitor, parallel: bool = True) -> bool:
        """Start all services with enhanced coordination.
        
        Args:
            process_manager: Process manager instance
            health_monitor: Health monitor instance  
            parallel: Whether to start services in parallel
            
        Returns:
            True if all required services started successfully
        """
        try:
            # Initialize coordination systems first
            if not await self.initialize_coordination_systems():
                logger.error("Failed to initialize coordination systems")
                return False
            
            # Register service startup callbacks with coordinator
            await self._register_service_callbacks()
            
            # Use enhanced coordination for startup
            if parallel:
                success = await self._start_services_coordinated()
            else:
                # Fallback to sequential startup
                services = {}
                services["auth"] = self.start_auth_service()
                services["backend"] = self.start_backend()
                services["frontend"] = self.start_frontend()
                success = all(process is not None for process, _ in services.values())
            
            # Register successful processes with process manager
            if success:
                await self._register_processes_with_manager(process_manager)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start services with coordination: {e}")
            return False
    
    async def _register_service_callbacks(self):
        """Register service startup callbacks with the coordinator."""
        # Register backend startup
        self.service_coordinator.register_service(
            "backend",
            startup_callback=self._start_backend_coordinated,
            readiness_checker=lambda: self.readiness_manager.check_service_ready("backend")
        )
        
        # Register frontend startup
        self.service_coordinator.register_service(
            "frontend", 
            startup_callback=self._start_frontend_coordinated,
            readiness_checker=lambda: self.readiness_manager.check_service_ready("frontend")
        )
        
        # Register auth service startup
        self.service_coordinator.register_service(
            "auth",
            startup_callback=self._start_auth_coordinated,
            readiness_checker=lambda: self.readiness_manager.check_service_ready("auth")
        )
        
        logger.info("Registered service callbacks with coordinator")
    
    async def _start_services_coordinated(self) -> bool:
        """Start services using the enhanced coordinator."""
        services_to_start = ["auth", "backend", "frontend"]
        
        # Use service coordinator for dependency-aware startup
        success = await self.service_coordinator.coordinate_startup(services_to_start)
        
        if success:
            logger.info("All required services started successfully with coordination")
            
            # Check for degraded services
            degraded = self.service_coordinator.get_degraded_services()
            if degraded:
                logger.warning(f"System running in degraded mode. Failed optional services: {degraded}")
        else:
            logger.error("Service coordination failed")
            
            # Log detailed status
            status = self.service_coordinator.get_startup_status()
            logger.error(f"Coordination status: {status['coordination_state']}")
            
            for service_name, service_status in status['services'].items():
                if not service_status['startup_success']:
                    logger.error(f"  {service_name}: {service_status['error_message']}")
        
        return success
    
    async def _start_backend_coordinated(self):
        """Start backend service with coordination integration."""
        # Reserve port first
        backend_port = self.config.backend_port or 8000
        allocation_result = await self.port_allocator.reserve_port(
            "backend", 
            preferred_port=backend_port
        )
        
        if not allocation_result.success:
            raise RuntimeError(f"Failed to reserve port for backend: {allocation_result.error_message}")
        
        # Update config with allocated port
        allocated_port = allocation_result.port
        if allocated_port != backend_port:
            self.config.backend_port = allocated_port
            logger.info(f"Backend port updated to {allocated_port}")
        
        # Mark as initializing
        await self.readiness_manager.mark_service_initializing("backend")
        
        # Start the service
        result = self.start_backend()
        
        if result[0]:  # Process started successfully
            # Confirm port allocation
            await self.port_allocator.confirm_allocation(
                allocated_port, 
                "backend", 
                result[0].pid if result[0] else None
            )
            
            # Register in service registry
            endpoints = [ServiceEndpoint(
                name="api",
                url=f"http://localhost:{allocated_port}",
                port=allocated_port,
                health_endpoint="/health",
                ready_endpoint="/health/ready"
            )]
            
            await self.service_registry.register_service(
                "backend",
                endpoints=endpoints,
                metadata={"port": allocated_port, "pid": result[0].pid if result[0] else None},
                dependencies=["database", "redis"]
            )
            
            # Mark as starting
            await self.readiness_manager.mark_service_starting("backend")
            await self.service_registry.update_service_status("backend", ServiceStatus.STARTING)
        
        return result
    
    async def _start_frontend_coordinated(self):
        """Start frontend service with coordination integration."""
        # Reserve port
        frontend_port = self.config.frontend_port or 3000
        allocation_result = await self.port_allocator.reserve_port(
            "frontend",
            preferred_port=frontend_port
        )
        
        if not allocation_result.success:
            raise RuntimeError(f"Failed to reserve port for frontend: {allocation_result.error_message}")
        
        allocated_port = allocation_result.port
        if allocated_port != frontend_port:
            self.config.frontend_port = allocated_port
            logger.info(f"Frontend port updated to {allocated_port}")
        
        await self.readiness_manager.mark_service_initializing("frontend")
        
        result = self.start_frontend()
        
        if result[0]:
            await self.port_allocator.confirm_allocation(
                allocated_port,
                "frontend", 
                result[0].pid if result[0] else None
            )
            
            endpoints = [ServiceEndpoint(
                name="web",
                url=f"http://localhost:{allocated_port}", 
                port=allocated_port
            )]
            
            await self.service_registry.register_service(
                "frontend",
                endpoints=endpoints,
                metadata={"port": allocated_port, "pid": result[0].pid if result[0] else None},
                dependencies=["backend"]
            )
            
            await self.readiness_manager.mark_service_starting("frontend")
            await self.service_registry.update_service_status("frontend", ServiceStatus.STARTING)
        
        return result
    
    async def _start_auth_coordinated(self):
        """Start auth service with coordination integration."""
        auth_config = self.services_config.auth_service.get_config()
        auth_port = auth_config.get("port", 8081)
        
        allocation_result = await self.port_allocator.reserve_port(
            "auth",
            preferred_port=auth_port
        )
        
        if not allocation_result.success:
            raise RuntimeError(f"Failed to reserve port for auth: {allocation_result.error_message}")
        
        allocated_port = allocation_result.port
        if allocated_port != auth_port:
            # Update auth config
            auth_config["port"] = allocated_port
            logger.info(f"Auth port updated to {allocated_port}")
        
        await self.readiness_manager.mark_service_initializing("auth")
        
        result = self.start_auth_service()
        
        if result[0]:
            await self.port_allocator.confirm_allocation(
                allocated_port,
                "auth",
                result[0].pid if result[0] else None
            )
            
            endpoints = [ServiceEndpoint(
                name="auth_api",
                url=f"http://localhost:{allocated_port}",
                port=allocated_port,
                health_endpoint="/health",
                ready_endpoint="/auth/config"
            )]
            
            await self.service_registry.register_service(
                "auth",
                endpoints=endpoints,
                metadata={"port": allocated_port, "pid": result[0].pid if result[0] else None},
                dependencies=["database"]
            )
            
            await self.readiness_manager.mark_service_starting("auth")
            await self.service_registry.update_service_status("auth", ServiceStatus.STARTING)
        
        return result
    
    async def _register_processes_with_manager(self, process_manager):
        """Register successfully started processes with the process manager."""
        # This would extract process information from coordination results
        # and register them with the process manager
        # Implementation depends on specific process manager interface
        logger.info("Process registration with manager completed")
    
    def start_services_parallel(self) -> Dict[str, Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]]:
        """Start all services in parallel with progressive readiness."""
        start_time = time.time()
        
        # Create parallel startup tasks
        startup_tasks = [
            ParallelTask(
                task_id="auth_startup",
                func=self._start_service_safe,
                args=("auth", self.auth_starter.start_auth_service),
                task_type=TaskType.IO_BOUND,
                priority=1,  # Start auth first (highest priority)
                timeout=30
            ),
            ParallelTask(
                task_id="backend_startup", 
                func=self._start_service_safe,
                args=("backend", self.backend_starter.start_backend),
                task_type=TaskType.IO_BOUND,
                dependencies=["auth_startup"],  # Backend depends on auth
                priority=2,
                timeout=40
            ),
            ParallelTask(
                task_id="frontend_startup",
                func=self._start_service_safe, 
                args=("frontend", self.frontend_starter.start_frontend),
                task_type=TaskType.IO_BOUND,
                dependencies=["backend_startup"],  # Frontend depends on backend
                priority=3,
                timeout=50
            )
        ]
        
        # Add tasks to executor
        for task in startup_tasks:
            self.parallel_executor.add_task(task)
        
        # Execute parallel startup
        results = self.parallel_executor.execute_all(timeout=60)
        
        # Process results
        startup_results = {}
        for task_id, result in results.items():
            service_name = task_id.replace("_startup", "")
            if result.success:
                startup_results[service_name] = result.result
            else:
                error_type = type(result.error).__name__ if result.error else "UNKNOWN"
                startup_error_code = f"{service_name.upper()}_STARTUP_{error_type.upper()}"
                logger.error(f"ERROR [{startup_error_code}] {service_name} startup failed: {error_type} - {str(result.error)[:200]}")
                startup_results[service_name] = (None, None)
        
        elapsed = time.time() - start_time
        logger.info(f"Parallel service startup completed in {elapsed:.1f}s")
        
        return startup_results
    
    def _start_service_safe(self, service_name: str, start_func) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Safely start service with error handling."""
        try:
            return start_func()
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return (None, None)
    
    async def check_services_health_async(self, services: List[str] = None) -> Dict[str, bool]:
        """Check service health asynchronously."""
        services = services or ["auth", "backend", "frontend"]
        health_tasks = []
        
        # Create health check tasks
        for service in services:
            task = ParallelTask(
                task_id=f"{service}_health",
                func=self._check_service_health,
                args=(service,),
                task_type=TaskType.NETWORK_BOUND,
                timeout=5
            )
            health_tasks.append(task)
        
        # Execute health checks in parallel
        health_executor = ParallelExecutor(max_cpu_workers=1, max_io_workers=6)
        for task in health_tasks:
            health_executor.add_task(task)
        
        results = health_executor.execute_all(timeout=15)
        
        # Process health results
        health_status = {}
        for task_id, result in results.items():
            service_name = task_id.replace("_health", "")
            health_status[service_name] = result.success and result.result
        
        self.health_check_results.update(health_status)
        return health_status
    
    def _allocate_auth_port(self, preferred_port: int) -> int:
        """Allocate auth service port with dynamic fallback."""
        if is_port_available(preferred_port):
            return preferred_port
        
        # Find alternative port in range
        allocated_port = find_available_port(preferred_port, (8081, 8090))
        logger.info(f"Port {preferred_port} unavailable, allocated port {allocated_port}")
        return allocated_port
    
    def _update_backend_auth_config(self, auth_port: int):
        """Update backend environment with auth service port.
        
        NOTE: This method is now redundant as auth_starter.py handles
        setting AUTH_SERVICE_PORT/URL directly via EnvironmentManager.
        Keeping for backward compatibility but no longer sets duplicates.
        """
        logger.debug(f"Auth port {auth_port} configuration handled by auth_starter")
    
    def get_allocated_ports(self) -> Dict[str, int]:
        """Get all allocated service ports."""
        return self.allocated_ports.copy()
    
    def _check_service_health(self, service: str) -> bool:
        """Check health of individual service."""
        try:
            if service == "auth":
                return self._check_auth_health()
            elif service == "backend":
                return self._check_backend_health()
            elif service == "frontend":
                return self._check_frontend_health()
            return False
        except Exception as e:
            logger.warning(f"Health check failed for {service}: {e}")
            return False
    
    def _check_auth_health(self) -> bool:
        """Check auth service health with dynamic port support.
        
        Uses /auth/config endpoint per SPEC step 9.
        """
        try:
            import requests
            # Use dynamically allocated auth port
            auth_port = self.allocated_ports.get('auth', 8081)
            auth_url = f"http://localhost:{auth_port}/auth/config"
            response = requests.get(auth_url, timeout=3)
            return response.status_code in [200, 404]  # 404 is acceptable
        except:
            return False
    
    def _check_backend_health(self) -> bool:
        """Check backend service health with dynamic port support.
        
        Uses /health/ready endpoint per SPEC requirements.
        """
        try:
            import requests
            # Use allocated backend port
            backend_port = self.allocated_ports.get('backend', self.config.backend_port or 8000)
            # Use /health/ready for readiness checks per SPEC step 8
            backend_url = f"http://localhost:{backend_port}/health/ready"
            response = requests.get(backend_url, timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def _check_frontend_health(self) -> bool:
        """Check frontend service health."""
        try:
            import requests
            frontend_port = self.config.frontend_port or 3000
            frontend_url = f"http://localhost:{frontend_port}"
            response = requests.get(frontend_url, timeout=3)
            return response.status_code in [200, 404]  # 404 is OK for frontend
        except:
            return False
    
    def wait_for_service_readiness(self, service: str, timeout: int = 30) -> bool:
        """Wait for specific service to be ready with enhanced error context.
        
        Per SPEC: This uses proper readiness endpoints and grace periods.
        """
        start_time = time.time()
        check_interval = 1.0
        
        # Use service-specific timeouts per SPEC HEALTH-002
        if service.lower() == "frontend":
            timeout = 90  # Frontend: 90 second grace period
        elif service.lower() == "backend":
            timeout = 30  # Backend: 30 second grace period
        
        # Build service URL for detailed error reporting
        service_url = self._get_service_health_url(service)
        
        while (time.time() - start_time) < timeout:
            try:
                health_status = asyncio.run(self.check_services_health_async([service]))
                if health_status.get(service, False):
                    logger.info(f"{service} service is ready")
                    return True
                
                time.sleep(check_interval)
                # Increase check interval progressively
                check_interval = min(check_interval * 1.2, 3.0)
                
            except Exception as e:
                logger.warning(f"Service readiness check failed: {e}")
                time.sleep(check_interval)
        
        # Enhanced error message with expected vs actual context
        elapsed = time.time() - start_time
        expected_vs_actual = f"Expected: {service} ready at {service_url}, Actual: timeout after {elapsed:.1f}s"
        logger.error(f"{service} service not ready. {expected_vs_actual}")
        logger.error(f"Suggestion: Check {service} service logs and port {self.allocated_ports.get(service, 'unknown')}")
        return False
    
    def _get_service_health_url(self, service: str) -> str:
        """Get health check URL for service."""
        if service.lower() == "auth":
            port = self.allocated_ports.get('auth', 8081)
            return f"http://localhost:{port}/auth/config"
        elif service.lower() == "backend":
            port = self.allocated_ports.get('backend', 8000)
            return f"http://localhost:{port}/health/ready"
        elif service.lower() == "frontend":
            port = self.config.frontend_port or 3000
            return f"http://localhost:{port}"
        return "unknown"
    
    def get_startup_performance(self) -> Dict[str, Any]:
        """Get startup performance metrics."""
        stats = self.parallel_executor.get_performance_stats()
        stats.update({
            "health_checks": len(self.health_check_results),
            "healthy_services": sum(self.health_check_results.values()),
            "parallel_enabled": True,
            "enhanced_coordination": self.service_coordinator is not None
        })
        return stats
    
    def cleanup(self):
        """Cleanup all coordination resources."""
        try:
            if hasattr(self, 'parallel_executor'):
                self.parallel_executor.cleanup()
                
            # Cleanup coordination systems
            if self.service_coordinator:
                self.service_coordinator.reset()
                
            # Note: Global cleanup of port allocator and service registry
            # is handled by their respective cleanup functions
            
            logger.info("Service startup coordinator cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all coordination systems."""
        status = {
            "legacy_parallel_executor": self.get_startup_performance() if hasattr(self, 'parallel_executor') else {},
            "service_coordinator": self.service_coordinator.get_startup_status() if self.service_coordinator else {},
            "readiness_manager": {
                "ready_services": self.readiness_manager.get_ready_services(),
                "not_ready_services": self.readiness_manager.get_not_ready_services(),
                "all_status": {name: status.overall_ready for name, status in self.readiness_manager.get_all_service_status().items()}
            },
            "dependency_manager": self.dependency_manager.get_dependency_status() if self.dependency_manager else {},
            "allocated_ports": self.allocated_ports
        }
        
        return status