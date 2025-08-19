"""
Service startup coordination for development launcher.
"""

import asyncio
import logging
import time
from typing import Optional, Tuple, Dict, Any, List
import subprocess
from concurrent.futures import ThreadPoolExecutor, Future

from dev_launcher.config import LauncherConfig
from dev_launcher.log_streamer import LogStreamer, LogManager
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.backend_starter import BackendStarter
from dev_launcher.frontend_starter import FrontendStarter
from dev_launcher.auth_starter import AuthStarter
from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType

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
        """Start the backend server."""
        return self.backend_starter.start_backend()
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server."""
        return self.frontend_starter.start_frontend()
    
    def start_auth_service(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the auth service."""
        return self.auth_starter.start_auth_service()
    
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
                timeout=15
            ),
            ParallelTask(
                task_id="backend_startup", 
                func=self._start_service_safe,
                args=("backend", self.backend_starter.start_backend),
                task_type=TaskType.IO_BOUND,
                dependencies=["auth_startup"],  # Backend depends on auth
                priority=2,
                timeout=20
            ),
            ParallelTask(
                task_id="frontend_startup",
                func=self._start_service_safe, 
                args=("frontend", self.frontend_starter.start_frontend),
                task_type=TaskType.IO_BOUND,
                dependencies=["backend_startup"],  # Frontend depends on backend
                priority=3,
                timeout=25
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
        """Check auth service health."""
        try:
            import requests
            auth_url = f"http://localhost:8081/health"
            response = requests.get(auth_url, timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def _check_backend_health(self) -> bool:
        """Check backend service health."""
        try:
            import requests
            backend_port = self.config.backend_port or 8000
            backend_url = f"http://localhost:{backend_port}/health"
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
        """Wait for specific service to be ready with progressive checks."""
        start_time = time.time()
        check_interval = 1.0
        
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
        
        logger.warning(f"{service} service not ready after {timeout}s")
        return False
    
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