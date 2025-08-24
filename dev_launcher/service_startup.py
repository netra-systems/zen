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
from dev_launcher.frontend_starter import FrontendStarter
from dev_launcher.log_streamer import LogManager, LogStreamer
from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    find_available_port,
    is_port_available,
    wait_for_service_with_details,
)

logger = logging.getLogger(__name__)


class ServiceStartupCoordinator:
    """
    Coordinates startup of development services with parallel execution.
    
    Enhanced coordinator that starts services in parallel with
    async health checks and progressive readiness validation.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize service startup coordinator."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.allocated_ports = {}  # Track allocated ports
        self._setup_starters()
        self._setup_parallel_execution()
    
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
                {"suggestion": "Check DATABASE_URL and ensure PostgreSQL is running"}
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
    
    def start_all_services(self, process_manager, health_monitor, parallel: bool = True) -> bool:
        """Start all services with unified approach.
        
        Args:
            process_manager: Process manager instance
            health_monitor: Health monitor instance  
            parallel: Whether to start services in parallel
            
        Returns:
            True if all services started successfully
        """
        try:
            if parallel:
                # Start services in parallel
                services = self.start_services_parallel()
            else:
                # Start services sequentially
                services = {}
                services["auth"] = self.start_auth_service()
                services["backend"] = self.start_backend()
                services["frontend"] = self.start_frontend()
            
            # Register processes with process manager
            for name, (process, streamer) in services.items():
                if process:
                    process_manager.add_process(name.capitalize(), process)
            
            # Verify all services started
            return all(process is not None for process, _ in services.values())
            
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            return False
    
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
                logger.error(f"{service_name} startup failed: {result.error}")
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
        
        Uses /api/auth/config endpoint per SPEC step 9.
        """
        try:
            import requests
            # Use dynamically allocated auth port
            auth_port = self.allocated_ports.get('auth', 8081)
            auth_url = f"http://localhost:{auth_port}/api/auth/config"
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
            return f"http://localhost:{port}/api/auth/config"
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
            "parallel_enabled": True
        })
        return stats
    
    def cleanup(self):
        """Cleanup parallel execution resources."""
        if hasattr(self, 'parallel_executor'):
            self.parallel_executor.cleanup()