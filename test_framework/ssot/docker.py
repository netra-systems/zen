"""
Single Source of Truth (SSOT) Docker Test Utility

This module provides the unified DockerTestUtility that wraps UnifiedDockerManager
for ALL Docker testing needs. It eliminates Docker test setup duplication.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Ensures consistent Docker environment setup, service orchestration, and reliable cleanup.

CRITICAL: This is the ONLY source for Docker test utilities in the system.
ALL Docker-based tests must use DockerTestUtility for container management.
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import SSOT environment management
from shared.isolated_environment import get_env

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import UnifiedDockerManager and related components
from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    ServiceHealth,
    ContainerInfo,
    OrchestrationConfig,
    EnvironmentType
)

logger = logging.getLogger(__name__)


class DockerTestEnvironmentType(Enum):
    """Docker test environment types."""
    ISOLATED = "isolated"          # Single test isolation
    DEDICATED = "dedicated"        # Dedicated test environment
    INTEGRATION = "integration"    # Integration test environment
    PERFORMANCE = "performance"    # Performance testing environment
    PARALLEL = "parallel"          # Parallel execution environment


@dataclass
class DockerTestMetrics:
    """Track Docker test performance and behavior metrics."""
    
    def __init__(self):
        self.startup_time = 0.0
        self.cleanup_time = 0.0
        self.services_started = 0
        self.services_failed = 0
        self.containers_created = 0
        self.containers_removed = 0
        self.health_check_duration = 0.0
        self.port_conflicts_resolved = 0
        self.restart_count = 0
        self.total_memory_usage_mb = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.service_health_history: Dict[str, List[ServiceHealth]] = {}
        
    def record_startup(self, duration: float):
        """Record startup timing."""
        self.startup_time = duration
        
    def record_cleanup(self, duration: float):
        """Record cleanup timing."""
        self.cleanup_time = duration
        
    def record_service_started(self, service_name: str):
        """Record successful service startup."""
        self.services_started += 1
        
    def record_service_failed(self, service_name: str, error: str):
        """Record service startup failure."""
        self.services_failed += 1
        self.errors.append(f"Service {service_name} failed: {error}")
        
    def record_container_created(self, container_name: str):
        """Record container creation."""
        self.containers_created += 1
        
    def record_container_removed(self, container_name: str):
        """Record container removal."""
        self.containers_removed += 1
        
    def record_health_check(self, duration: float):
        """Record health check timing."""
        self.health_check_duration = duration
        
    def record_port_conflict_resolved(self):
        """Record port conflict resolution."""
        self.port_conflicts_resolved += 1
        
    def record_restart(self):
        """Record service restart."""
        self.restart_count += 1
        
    def record_service_health(self, service_name: str, health: ServiceHealth):
        """Record service health status."""
        if service_name not in self.service_health_history:
            self.service_health_history[service_name] = []
        self.service_health_history[service_name].append(health)
        
    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
        
    def add_warning(self, warning: str):
        """Record a warning."""
        self.warnings.append(warning)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "startup_time": self.startup_time,
            "cleanup_time": self.cleanup_time,
            "services_started": self.services_started,
            "services_failed": self.services_failed,
            "containers_created": self.containers_created,
            "containers_removed": self.containers_removed,
            "health_check_duration": self.health_check_duration,
            "port_conflicts_resolved": self.port_conflicts_resolved,
            "restart_count": self.restart_count,
            "total_memory_usage_mb": self.total_memory_usage_mb,
            "errors": self.errors,
            "warnings": self.warnings,
            "service_health_summary": {
                name: len(history) for name, history in self.service_health_history.items()
            }
        }


class DockerTestUtility:
    """
    Single Source of Truth (SSOT) utility for ALL Docker testing needs.
    
    This utility provides:
    - Consistent Docker environment management
    - Service orchestration and health monitoring
    - Port conflict resolution and management
    - Container lifecycle management
    - Performance monitoring and metrics
    - Multi-environment test support
    
    Features:
    - Automatic Docker service startup/cleanup
    - Service health verification
    - Port allocation and conflict resolution
    - Container introspection and monitoring
    - Resource usage tracking
    - Test isolation and cleanup
    - Cross-platform compatibility
    
    Usage:
        async with DockerTestUtility() as docker_util:
            services = await docker_util.start_services(["postgres", "redis"])
            # Test with services running
            # Automatic cleanup on exit
    """
    
    def __init__(self, 
                 environment_type: DockerTestEnvironmentType = DockerTestEnvironmentType.ISOLATED,
                 env: Optional[Any] = None):
        """
        Initialize DockerTestUtility.
        
        Args:
            environment_type: Type of Docker test environment
            env: Environment manager instance
        """
        self.env = env or get_env()
        self.environment_type = environment_type
        self.test_id = f"dockertest_{uuid.uuid4().hex[:8]}"
        self.metrics = DockerTestMetrics()
        
        # Docker manager instance
        self.docker_manager: Optional[UnifiedDockerManager] = None
        self.environment_name: Optional[str] = None
        self.allocated_ports: Dict[str, int] = {}
        
        # Service tracking
        self.running_services: Set[str] = set()
        self.container_info: Dict[str, ContainerInfo] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Configuration
        self.docker_config = self._get_docker_config()
        
        # State tracking
        self.is_initialized = False
        self.cleanup_registered = False
        
        logger.debug(f"DockerTestUtility initialized: {environment_type.value} [{self.test_id}]")
    
    def _get_docker_config(self) -> Dict[str, Any]:
        """Get Docker configuration from environment."""
        return {
            "startup_timeout": float(self.env.get("DOCKER_STARTUP_TIMEOUT", "120")),
            "health_check_timeout": float(self.env.get("DOCKER_HEALTH_TIMEOUT", "30")),
            "health_check_retries": int(self.env.get("DOCKER_HEALTH_RETRIES", "20")),
            "cleanup_timeout": float(self.env.get("DOCKER_CLEANUP_TIMEOUT", "60")),
            "enable_metrics": self.env.get("DOCKER_ENABLE_METRICS", "true").lower() == "true",
            "memory_limit_mb": int(self.env.get("DOCKER_MEMORY_LIMIT_MB", "2048")),
            "auto_cleanup": self.env.get("DOCKER_AUTO_CLEANUP", "true").lower() == "true"
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize Docker test environment."""
        if self.is_initialized:
            return
            
        start_time = time.time()
        
        try:
            # Create Docker manager instance
            self.docker_manager = UnifiedDockerManager()
            
            # Initialize Docker manager
            await self.docker_manager.initialize()
            
            # Verify Docker is running
            await self._verify_docker_availability()
            
            # Prepare environment name
            self.environment_name = self._generate_environment_name()
            
            self.is_initialized = True
            self.metrics.record_startup(time.time() - start_time)
            
            logger.info(f"DockerTestUtility initialized in {self.metrics.startup_time:.2f}s")
            
        except Exception as e:
            self.metrics.add_error(f"Initialization failed: {str(e)}")
            logger.error(f"Docker test utility initialization failed: {e}")
            raise
    
    def _generate_environment_name(self) -> str:
        """Generate unique environment name for this test session."""
        env_type = self.environment_type.value
        timestamp = int(time.time())
        return f"{env_type}_{self.test_id}_{timestamp}"
    
    async def _verify_docker_availability(self):
        """Verify Docker is available and responding."""
        try:
            if not self.docker_manager:
                raise RuntimeError("Docker manager not initialized")
                
            # Test basic Docker connectivity
            available = await self.docker_manager.is_docker_available()
            if not available:
                raise RuntimeError("Docker is not available or not responding")
            
            logger.debug("Docker availability verified")
            
        except Exception as e:
            raise RuntimeError(f"Docker not available: {e}")
    
    # ========== Service Management ==========
    
    async def start_services(self, 
                           services: List[str],
                           wait_for_health: bool = True,
                           timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Start specified Docker services for testing.
        
        Args:
            services: List of service names to start
            wait_for_health: Whether to wait for services to be healthy
            timeout: Optional timeout override
            
        Returns:
            Dictionary with service startup results
        """
        if not self.is_initialized:
            await self.initialize()
        
        timeout = timeout or self.docker_config["startup_timeout"]
        start_time = time.time()
        
        logger.info(f"Starting Docker services: {services}")
        
        try:
            # Create orchestration config
            config = OrchestrationConfig(
                environment=self.environment_name,
                startup_timeout=timeout,
                health_check_timeout=self.docker_config["health_check_timeout"],
                health_check_retries=self.docker_config["health_check_retries"],
                required_services=services
            )
            
            # Start services using Docker manager
            result = await self.docker_manager.start_services_async(
                services=services,
                config=config,
                wait_for_health=wait_for_health
            )
            
            # Update tracking
            if result.success:
                self.running_services.update(services)
                
                # Get port mappings
                ports = await self.docker_manager.get_service_ports(self.environment_name)
                self.allocated_ports.update(ports)
                
                # Get container info
                container_info = await self.docker_manager.get_container_info(services)
                self.container_info.update(container_info)
                
                # Record metrics
                for service in services:
                    self.metrics.record_service_started(service)
                    
                logger.info(f"Successfully started services: {services}")
            else:
                for error in result.errors:
                    self.metrics.add_error(error)
                logger.error(f"Failed to start some services: {result.errors}")
            
            startup_duration = time.time() - start_time
            
            return {
                "success": result.success,
                "services_started": list(result.services_started),
                "services_failed": list(result.services_failed),
                "startup_duration": startup_duration,
                "ports": self.allocated_ports,
                "errors": result.errors
            }
            
        except Exception as e:
            self.metrics.add_error(f"Service startup failed: {str(e)}")
            logger.error(f"Failed to start services {services}: {e}")
            raise
    
    async def stop_services(self, 
                          services: Optional[List[str]] = None,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Stop specified services or all running services.
        
        Args:
            services: Optional list of services to stop (default: all running)
            timeout: Optional timeout override
            
        Returns:
            Dictionary with service stop results
        """
        if not self.docker_manager:
            return {"success": True, "message": "No services to stop"}
        
        services_to_stop = services or list(self.running_services)
        timeout = timeout or self.docker_config["cleanup_timeout"]
        
        if not services_to_stop:
            return {"success": True, "message": "No services to stop"}
        
        logger.info(f"Stopping Docker services: {services_to_stop}")
        
        start_time = time.time()
        stop_results = {}
        
        try:
            for service in services_to_stop:
                try:
                    await self.docker_manager.stop_service(service, timeout=timeout)
                    stop_results[service] = {"success": True}
                    
                    # Update tracking
                    self.running_services.discard(service)
                    self.container_info.pop(service, None)
                    self.service_health.pop(service, None)
                    
                except Exception as e:
                    stop_results[service] = {"success": False, "error": str(e)}
                    self.metrics.add_error(f"Failed to stop {service}: {str(e)}")
            
            stop_duration = time.time() - start_time
            successful_stops = sum(1 for result in stop_results.values() if result["success"])
            
            logger.info(f"Stopped {successful_stops}/{len(services_to_stop)} services in {stop_duration:.2f}s")
            
            return {
                "success": successful_stops == len(services_to_stop),
                "services_stopped": successful_stops,
                "stop_duration": stop_duration,
                "results": stop_results
            }
            
        except Exception as e:
            self.metrics.add_error(f"Service stop failed: {str(e)}")
            logger.error(f"Failed to stop services: {e}")
            raise
    
    async def restart_service(self, service_name: str, timeout: Optional[float] = None) -> bool:
        """
        Restart a specific service.
        
        Args:
            service_name: Name of service to restart
            timeout: Optional timeout override
            
        Returns:
            True if restart successful
        """
        logger.info(f"Restarting Docker service: {service_name}")
        
        try:
            timeout = timeout or self.docker_config["startup_timeout"]
            
            # Stop service
            await self.stop_services([service_name], timeout=timeout/2)
            
            # Wait briefly
            await asyncio.sleep(2.0)
            
            # Start service
            result = await self.start_services([service_name], timeout=timeout/2)
            
            if result["success"]:
                self.metrics.record_restart()
                logger.info(f"Successfully restarted service: {service_name}")
                return True
            else:
                logger.error(f"Failed to restart service {service_name}: {result.get('errors')}")
                return False
                
        except Exception as e:
            self.metrics.add_error(f"Service restart failed: {str(e)}")
            logger.error(f"Failed to restart service {service_name}: {e}")
            return False
    
    # ========== Health Monitoring ==========
    
    async def check_service_health(self, service_name: str, timeout: Optional[float] = None) -> ServiceHealth:
        """
        Check health of a specific service.
        
        Args:
            service_name: Name of service to check
            timeout: Optional timeout override
            
        Returns:
            ServiceHealth object with current status
        """
        timeout = timeout or self.docker_config["health_check_timeout"]
        
        try:
            health = await self.docker_manager.check_service_health_async(service_name, timeout)
            
            # Update tracking
            self.service_health[service_name] = health
            self.metrics.record_service_health(service_name, health)
            
            return health
            
        except Exception as e:
            error_health = ServiceHealth(
                service_name=service_name,
                is_healthy=False,
                port=0,
                response_time_ms=0.0,
                error_message=str(e),
                last_check=time.time()
            )
            
            self.service_health[service_name] = error_health
            self.metrics.add_error(f"Health check failed for {service_name}: {str(e)}")
            
            return error_health
    
    async def check_all_services_health(self, timeout: Optional[float] = None) -> Dict[str, ServiceHealth]:
        """
        Check health of all running services.
        
        Args:
            timeout: Optional timeout override
            
        Returns:
            Dictionary mapping service names to ServiceHealth objects
        """
        if not self.running_services:
            return {}
        
        health_start = time.time()
        
        # Check all services concurrently
        tasks = [
            self.check_service_health(service, timeout)
            for service in self.running_services
        ]
        
        try:
            health_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            health_dict = {}
            for i, result in enumerate(health_results):
                service = list(self.running_services)[i]
                if isinstance(result, ServiceHealth):
                    health_dict[service] = result
                else:
                    # Handle exception
                    error_health = ServiceHealth(
                        service_name=service,
                        is_healthy=False,
                        port=0,
                        response_time_ms=0.0,
                        error_message=str(result),
                        last_check=time.time()
                    )
                    health_dict[service] = error_health
                    self.metrics.add_error(f"Health check exception for {service}: {str(result)}")
            
            health_duration = time.time() - health_start
            self.metrics.record_health_check(health_duration)
            
            healthy_count = sum(1 for h in health_dict.values() if h.is_healthy)
            logger.info(f"Health check completed: {healthy_count}/{len(health_dict)} services healthy")
            
            return health_dict
            
        except Exception as e:
            self.metrics.add_error(f"Health check batch failed: {str(e)}")
            logger.error(f"Failed to check service health: {e}")
            raise
    
    async def wait_for_services_healthy(self, 
                                      services: Optional[List[str]] = None,
                                      timeout: Optional[float] = None) -> bool:
        """
        Wait for services to become healthy.
        
        Args:
            services: Optional list of services to wait for (default: all running)
            timeout: Optional timeout override
            
        Returns:
            True if all services became healthy
        """
        services_to_check = services or list(self.running_services)
        timeout = timeout or self.docker_config["startup_timeout"]
        
        if not services_to_check:
            return True
        
        logger.info(f"Waiting for services to become healthy: {services_to_check}")
        
        start_time = time.time()
        check_interval = 2.0
        
        while (time.time() - start_time) < timeout:
            try:
                # Check health of all services
                health_results = await self.check_all_services_health()
                
                # Check if all required services are healthy
                all_healthy = True
                for service in services_to_check:
                    if service not in health_results:
                        all_healthy = False
                        break
                    if not health_results[service].is_healthy:
                        all_healthy = False
                        break
                
                if all_healthy:
                    wait_duration = time.time() - start_time
                    logger.info(f"All services healthy after {wait_duration:.2f}s")
                    return True
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"Health check error (retrying): {e}")
                await asyncio.sleep(check_interval)
        
        # Timeout reached
        final_health = await self.check_all_services_health()
        unhealthy = [name for name, health in final_health.items() 
                    if name in services_to_check and not health.is_healthy]
        
        logger.error(f"Timeout waiting for services to become healthy. Unhealthy: {unhealthy}")
        return False
    
    # ========== Port Management ==========
    
    def get_service_port(self, service_name: str) -> Optional[int]:
        """
        Get the allocated port for a service.
        
        Args:
            service_name: Name of service
            
        Returns:
            Port number if allocated, None otherwise
        """
        return self.allocated_ports.get(service_name)
    
    def get_service_url(self, service_name: str, protocol: str = "http") -> Optional[str]:
        """
        Get the full URL for a service.
        
        Args:
            service_name: Name of service
            protocol: Protocol (http, https, ws, wss)
            
        Returns:
            Full service URL if port is allocated
        """
        port = self.get_service_port(service_name)
        if port is None:
            return None
        
        return f"{protocol}://localhost:{port}"
    
    def get_all_service_urls(self) -> Dict[str, str]:
        """Get URLs for all running services."""
        return {
            service: self.get_service_url(service)
            for service in self.running_services
            if self.get_service_port(service) is not None
        }
    
    # ========== Container Management ==========
    
    async def get_container_logs(self, service_name: str, lines: int = 100) -> str:
        """
        Get logs from a service container.
        
        Args:
            service_name: Name of service
            lines: Number of log lines to retrieve
            
        Returns:
            Container logs as string
        """
        try:
            if not self.docker_manager:
                return "Docker manager not initialized"
            
            logs = await self.docker_manager.get_container_logs(service_name, lines)
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get container logs for {service_name}: {e}")
            return f"Error getting logs: {str(e)}"
    
    async def execute_in_container(self, 
                                 service_name: str,
                                 command: str,
                                 timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a command in a service container.
        
        Args:
            service_name: Name of service
            command: Command to execute
            timeout: Optional timeout override
            
        Returns:
            Execution result with stdout, stderr, and return code
        """
        try:
            if not self.docker_manager:
                raise RuntimeError("Docker manager not initialized")
            
            result = await self.docker_manager.execute_in_container(
                service_name, 
                command, 
                timeout or 30.0
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute command in {service_name}: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    # ========== Environment Management ==========
    
    @asynccontextmanager
    async def service_environment(self, services: List[str]) -> AsyncGenerator[Dict[str, str], None]:
        """
        Context manager for a complete service environment.
        
        Args:
            services: List of services to start
            
        Yields:
            Dictionary of service URLs
        """
        try:
            # Start services
            result = await self.start_services(services, wait_for_health=True)
            
            if not result["success"]:
                raise RuntimeError(f"Failed to start services: {result.get('errors')}")
            
            # Yield service URLs
            yield self.get_all_service_urls()
            
        finally:
            # Stop services
            await self.stop_services(services)
    
    async def create_isolated_environment(self, services: List[str]) -> str:
        """
        Create an isolated test environment with unique ports.
        
        Args:
            services: List of services for the environment
            
        Returns:
            Environment identifier
        """
        env_id = f"isolated_{uuid.uuid4().hex[:8]}"
        
        try:
            # Use the Docker manager to create isolated environment
            if self.docker_manager:
                success = await self.docker_manager.acquire_environment(
                    env_name=env_id,
                    services=services,
                    environment_type=EnvironmentType.DEDICATED
                )
                
                if success:
                    logger.info(f"Created isolated environment: {env_id}")
                    return env_id
                else:
                    raise RuntimeError(f"Failed to create isolated environment: {env_id}")
            else:
                raise RuntimeError("Docker manager not initialized")
                
        except Exception as e:
            self.metrics.add_error(f"Failed to create isolated environment: {str(e)}")
            logger.error(f"Failed to create isolated environment: {e}")
            raise
    
    async def destroy_isolated_environment(self, env_id: str) -> bool:
        """
        Destroy an isolated test environment.
        
        Args:
            env_id: Environment identifier
            
        Returns:
            True if successfully destroyed
        """
        try:
            if self.docker_manager:
                success = await self.docker_manager.release_environment(env_id)
                
                if success:
                    logger.info(f"Destroyed isolated environment: {env_id}")
                else:
                    logger.warning(f"Failed to destroy isolated environment: {env_id}")
                
                return success
            else:
                logger.warning("Docker manager not initialized")
                return False
                
        except Exception as e:
            self.metrics.add_error(f"Failed to destroy isolated environment: {str(e)}")
            logger.error(f"Failed to destroy isolated environment {env_id}: {e}")
            return False
    
    # ========== Cleanup and Resource Management ==========
    
    async def cleanup(self):
        """Clean up all Docker resources and state."""
        if not self.docker_manager:
            return
        
        cleanup_start = time.time()
        
        try:
            logger.info(f"Starting Docker test utility cleanup")
            
            # Stop all running services
            if self.running_services:
                await self.stop_services(list(self.running_services))
            
            # Clean up environment if created
            if self.environment_name:
                await self.docker_manager.release_environment(self.environment_name)
            
            # Clean up Docker manager
            await self.docker_manager.cleanup()
            
            # Clear tracking state
            self.running_services.clear()
            self.allocated_ports.clear()
            self.container_info.clear()
            self.service_health.clear()
            
            cleanup_duration = time.time() - cleanup_start
            self.metrics.record_cleanup(cleanup_duration)
            
            logger.info(f"Docker test utility cleanup completed in {cleanup_duration:.2f}s")
            
            # Log metrics if there were issues or long cleanup
            if self.metrics.errors or self.metrics.warnings or cleanup_duration > 10.0:
                logger.info(f"Docker test metrics: {self.metrics.to_dict()}")
                
        except Exception as e:
            logger.error(f"Docker test utility cleanup failed: {e}")
    
    # ========== Status and Monitoring ==========
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary."""
        return {
            "test_id": self.test_id,
            "environment_type": self.environment_type.value,
            "environment_name": self.environment_name,
            "is_initialized": self.is_initialized,
            "running_services": list(self.running_services),
            "allocated_ports": dict(self.allocated_ports),
            "service_health": {
                name: {
                    "is_healthy": health.is_healthy,
                    "port": health.port,
                    "response_time_ms": health.response_time_ms,
                    "error_message": health.error_message
                }
                for name, health in self.service_health.items()
            },
            "metrics": self.metrics.to_dict()
        }
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        if not self.docker_manager:
            return {"error": "Docker manager not initialized"}
        
        try:
            # Get fresh health check
            current_health = await self.check_all_services_health()
            
            # Get container info
            container_statuses = {}
            for service in self.running_services:
                try:
                    info = await self.docker_manager.get_container_info([service])
                    container_statuses.update(info)
                except Exception as e:
                    container_statuses[service] = f"Error: {str(e)}"
            
            # Generate report
            report = {
                "timestamp": datetime.now().isoformat(),
                "test_id": self.test_id,
                "environment": self.environment_name,
                "overall_health": all(h.is_healthy for h in current_health.values()),
                "services": {
                    name: {
                        "health": {
                            "is_healthy": health.is_healthy,
                            "port": health.port,
                            "response_time_ms": health.response_time_ms,
                            "error_message": health.error_message,
                            "last_check": health.last_check
                        },
                        "container": container_statuses.get(name, "No info available")
                    }
                    for name, health in current_health.items()
                },
                "metrics": self.metrics.to_dict(),
                "docker_manager_status": await self.docker_manager.get_health_report() if self.docker_manager else None
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


# ========== Specialized Docker Utilities ==========

class PostgreSQLDockerUtility(DockerTestUtility):
    """Specialized Docker utility for PostgreSQL testing."""
    
    async def create_test_database(self, database_name: str) -> bool:
        """Create a test database in PostgreSQL container."""
        try:
            result = await self.execute_in_container(
                "postgres",
                f"createdb -U postgres {database_name}",
                timeout=30.0
            )
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to create test database {database_name}: {e}")
            return False
    
    async def drop_test_database(self, database_name: str) -> bool:
        """Drop a test database from PostgreSQL container."""
        try:
            result = await self.execute_in_container(
                "postgres",
                f"dropdb -U postgres {database_name}",
                timeout=30.0
            )
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to drop test database {database_name}: {e}")
            return False


class RedisDockerUtility(DockerTestUtility):
    """Specialized Docker utility for Redis testing."""
    
    async def flush_redis_db(self, db_number: int = 0) -> bool:
        """Flush a specific Redis database."""
        try:
            result = await self.execute_in_container(
                "redis",
                f"redis-cli -n {db_number} FLUSHDB",
                timeout=10.0
            )
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to flush Redis DB {db_number}: {e}")
            return False


# ========== Factory Functions ==========

def create_docker_test_utility(
    environment_type: DockerTestEnvironmentType = DockerTestEnvironmentType.ISOLATED,
    services: Optional[List[str]] = None,
    env: Optional[Any] = None
) -> DockerTestUtility:
    """
    Factory function to create appropriate DockerTestUtility.
    
    Args:
        environment_type: Type of test environment
        services: Optional services list to determine specialization
        env: Environment manager
        
    Returns:
        DockerTestUtility instance (potentially specialized)
    """
    # If only PostgreSQL, use specialized utility
    if services and set(services) == {"postgres"}:
        return PostgreSQLDockerUtility(environment_type, env)
    
    # If only Redis, use specialized utility
    elif services and set(services) == {"redis"}:
        return RedisDockerUtility(environment_type, env)
    
    # Otherwise use general utility
    else:
        return DockerTestUtility(environment_type, env)


# ========== Global Docker Utility Management ==========

_global_docker_utilities: Dict[str, DockerTestUtility] = {}


async def get_docker_test_utility(
    environment_type: DockerTestEnvironmentType = DockerTestEnvironmentType.DEDICATED
) -> DockerTestUtility:
    """Get or create a global Docker test utility."""
    global _global_docker_utilities
    
    key = environment_type.value
    
    if key not in _global_docker_utilities:
        utility = create_docker_test_utility(environment_type)
        await utility.initialize()
        _global_docker_utilities[key] = utility
    
    return _global_docker_utilities[key]


async def cleanup_all_docker_utilities():
    """Clean up all global Docker utilities."""
    global _global_docker_utilities
    
    for utility in _global_docker_utilities.values():
        try:
            await utility.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up Docker utility: {e}")
    
    _global_docker_utilities.clear()


# Export SSOT Docker utilities
__all__ = [
    'DockerTestUtility',
    'PostgreSQLDockerUtility',
    'RedisDockerUtility',
    'DockerTestEnvironmentType',
    'DockerTestMetrics',
    'create_docker_test_utility',
    'get_docker_test_utility',
    'cleanup_all_docker_utilities'
]