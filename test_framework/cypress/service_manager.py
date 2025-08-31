"""
Service Dependency Manager for Cypress E2E Tests.

Manages service availability, health checks, and dependency resolution
for Cypress test execution, integrating with existing dev launcher infrastructure.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests
import psycopg2
import redis

# Import existing dev launcher infrastructure
from dev_launcher.docker_services import DockerServiceManager, check_docker_availability
from dev_launcher.service_availability_checker import ServiceAvailabilityChecker
from shared.isolated_environment import get_env
from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealthStatus:
    """Health status of a service."""
    
    name: str
    healthy: bool
    url: Optional[str] = None
    port: Optional[int] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ServiceDependencyManager:
    """
    Manages service dependencies for Cypress E2E tests.
    
    Integrates with existing dev launcher infrastructure to:
    - Check service availability
    - Start Docker containers as needed
    - Perform health checks
    - Wait for service readiness
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize service dependency manager.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.env = get_env()
        
        # Check Docker availability once during initialization
        self.docker_available = check_docker_availability()
        
        # Initialize existing infrastructure
        self.docker_manager = DockerServiceManager() if self.docker_available else None
        self.availability_checker = ServiceAvailabilityChecker()
        
        # Initialize port discovery
        self.port_discovery = DockerPortDiscovery()
        
        # Service configuration - will be updated with discovered ports
        self.required_services = self._get_required_services()
        
    def _get_required_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration for all required services with discovered ports.
        
        Returns:
            Service configuration dictionary
        """
        # Get discovered port mappings
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Build service configuration with actual ports
        services = {}
        
        # Backend service
        backend_mapping = port_mappings.get("backend")
        services["backend"] = {
            "name": "Netra Backend",
            "type": "http",
            "host": "localhost",
            "port": backend_mapping.external_port if backend_mapping else 8000,
            "health_endpoint": "/api/health",
            "timeout": 30,
            "required": True,
            "discovered": backend_mapping is not None
        }
        
        # Frontend service
        frontend_mapping = port_mappings.get("frontend")
        services["frontend"] = {
            "name": "Frontend Dev Server",
            "type": "http", 
            "host": "localhost",
            "port": frontend_mapping.external_port if frontend_mapping else 3000,
            "health_endpoint": "/",
            "timeout": 30,
            "required": True,
            "discovered": frontend_mapping is not None
        }
        
        # PostgreSQL service
        postgres_mapping = port_mappings.get("postgres")
        services["postgres"] = {
            "name": "PostgreSQL Database",
            "type": "database",
            "host": "localhost",
            "port": postgres_mapping.external_port if postgres_mapping else 5432,
            "database": "netra_dev",
            "timeout": 30,
            "required": True,
            "docker_fallback": True,
            "discovered": postgres_mapping is not None
        }
        
        # Redis service
        redis_mapping = port_mappings.get("redis")
        services["redis"] = {
            "name": "Redis Cache",
            "type": "cache",
            "host": "localhost",
            "port": redis_mapping.external_port if redis_mapping else 6379,
            "timeout": 15,
            "required": True,
            "docker_fallback": True,
            "discovered": redis_mapping is not None
        }
        
        return services
        
    async def ensure_all_services_ready(self, timeout: int = 300) -> Dict[str, Dict[str, Any]]:
        """
        Ensure all required services are ready for Cypress tests.
        
        Args:
            timeout: Maximum time to wait for all services
            
        Returns:
            Dictionary of service statuses
        """
        logger.info("Ensuring all services are ready for Cypress tests...")
        
        start_time = time.time()
        service_statuses = {}
        
        # Try to start missing services via docker-compose if needed
        required_service_names = list(self.required_services.keys())
        services_available, missing = self.port_discovery.ensure_services_available(required_service_names)
        
        if not services_available and missing:
            logger.info(f"Missing services detected: {list(missing.keys())}")
            
            # Try to start missing services
            success, started = self.port_discovery.start_missing_services(required_service_names)
            if success:
                logger.info(f"Started missing services: {started}")
                # Give services time to initialize
                await asyncio.sleep(5)
                # Refresh service configuration with new ports
                self.required_services = self._get_required_services()
            else:
                # Fall back to manual Docker container startup
                await self._start_docker_services_if_needed()
                # Refresh service configuration after startup
                self.required_services = self._get_required_services()
        
        # Check each service
        for service_name, config in self.required_services.items():
            logger.info(f"Checking service: {service_name} on port {config['port']}")
            
            remaining_timeout = max(0, timeout - int(time.time() - start_time))
            status = await self._ensure_service_ready(service_name, config, remaining_timeout)
            service_statuses[service_name] = status
            
            if config.get("required", True) and not status["healthy"]:
                logger.error(f"Required service {service_name} is not healthy on port {config['port']}")
                
        # Save discovered ports for Cypress to use
        self._save_port_config_for_cypress(service_statuses)
                
        return service_statuses
        
    def get_docker_status_info(self) -> Dict[str, Any]:
        """
        Get information about Docker availability and its impact on services.
        
        Returns:
            Dictionary with Docker status and affected services
        """
        docker_dependent_services = [
            name for name, config in self.required_services.items() 
            if config.get("docker_fallback", False)
        ]
        
        return {
            "docker_available": self.docker_available,
            "docker_dependent_services": docker_dependent_services,
            "can_fallback_to_docker": self.docker_available,
            "fallback_message": (
                "Docker services available for fallback" if self.docker_available 
                else "Docker not available - ensure local services are running"
            )
        }
        
    async def _start_docker_services_if_needed(self):
        """Start Docker services for databases/cache if local services not available."""
        logger.info("Checking if Docker services need to be started...")
        
        # Skip Docker operations if Docker is not available
        if not self.docker_available:
            logger.warning("Docker is not available - skipping Docker service startup")
            return
        
        # Check PostgreSQL
        postgres_available = await self._check_service_health("postgres", self.required_services["postgres"])
        if not postgres_available.healthy:
            logger.info("Starting PostgreSQL Docker container...")
            success, message = self.docker_manager.start_postgres_container()
            if success:
                logger.info(f"PostgreSQL container started: {message}")
            else:
                logger.warning(f"Failed to start PostgreSQL container: {message}")
                
        # Check Redis
        redis_available = await self._check_service_health("redis", self.required_services["redis"])
        if not redis_available.healthy:
            logger.info("Starting Redis Docker container...")
            success, message = self.docker_manager.start_redis_container()
            if success:
                logger.info(f"Redis container started: {message}")
            else:
                logger.warning(f"Failed to start Redis container: {message}")
                
    async def _ensure_service_ready(self, service_name: str, config: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """
        Ensure a specific service is ready.
        
        Args:
            service_name: Name of the service
            config: Service configuration
            timeout: Timeout in seconds
            
        Returns:
            Service status dictionary
        """
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < timeout:
            status = await self._check_service_health(service_name, config)
            
            if status.healthy:
                return {
                    "name": status.name,
                    "healthy": True,
                    "url": status.url,
                    "port": status.port,
                    "response_time_ms": status.response_time_ms,
                    "details": status.details
                }
                
            last_error = status.error
            logger.debug(f"Service {service_name} not ready, waiting... ({status.error})")
            await asyncio.sleep(2)
            
        return {
            "name": config["name"],
            "healthy": False,
            "url": f"http://{config['host']}:{config['port']}",
            "port": config["port"],
            "error": last_error or f"Timeout after {timeout}s",
            "details": {}
        }
        
    async def _check_service_health(self, service_name: str, config: Dict[str, Any]) -> ServiceHealthStatus:
        """
        Check health of a specific service.
        
        Args:
            service_name: Name of the service
            config: Service configuration
            
        Returns:
            Service health status
        """
        service_type = config.get("type", "http")
        
        if service_type == "http":
            return await self._check_http_service_health(service_name, config)
        elif service_type == "database":
            return await self._check_database_health(service_name, config)
        elif service_type == "cache":
            return await self._check_redis_health(service_name, config)
        else:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                error=f"Unknown service type: {service_type}"
            )
            
    async def _check_http_service_health(self, service_name: str, config: Dict[str, Any]) -> ServiceHealthStatus:
        """Check health of HTTP service."""
        host = config["host"]
        port = config["port"]
        endpoint = config.get("health_endpoint", "/")
        timeout = config.get("timeout", 30)
        
        url = f"http://{host}:{port}{endpoint}"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            healthy = response.status_code < 400
            
            return ServiceHealthStatus(
                name=config["name"],
                healthy=healthy,
                url=url,
                port=port,
                response_time_ms=response_time,
                details={
                    "status_code": response.status_code,
                    "content_length": len(response.content) if hasattr(response, 'content') else 0
                }
            )
            
        except requests.exceptions.ConnectionError:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=url,
                port=port,
                error="Connection refused"
            )
        except requests.exceptions.Timeout:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=url,
                port=port,
                error=f"Timeout after {timeout}s"
            )
        except Exception as e:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=url,
                port=port,
                error=str(e)
            )
            
    async def _check_database_health(self, service_name: str, config: Dict[str, Any]) -> ServiceHealthStatus:
        """Check health of PostgreSQL database."""
        host = config["host"]
        port = config["port"]
        database = config.get("database", "netra_dev")
        
        # Get database credentials from environment
        username = self.env.get("POSTGRES_USER", "postgres")
        password = self.env.get("POSTGRES_PASSWORD", "postgres")
        
        try:
            start_time = time.time()
            
            connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=config.get("timeout", 30)
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000
            
            cursor.close()
            connection.close()
            
            return ServiceHealthStatus(
                name=config["name"],
                healthy=True,
                url=f"postgresql://{username}@{host}:{port}/{database}",
                port=port,
                response_time_ms=response_time,
                details={
                    "database": database,
                    "username": username
                }
            )
            
        except psycopg2.OperationalError as e:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=f"postgresql://{username}@{host}:{port}/{database}",
                port=port,
                error=f"Database connection failed: {str(e)}"
            )
        except Exception as e:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=f"postgresql://{username}@{host}:{port}/{database}",
                port=port,
                error=str(e)
            )
            
    async def _check_redis_health(self, service_name: str, config: Dict[str, Any]) -> ServiceHealthStatus:
        """Check health of Redis cache."""
        host = config["host"]
        port = config["port"]
        
        try:
            start_time = time.time()
            
            client = redis.Redis(
                host=host,
                port=port,
                socket_timeout=config.get("timeout", 15),
                socket_connect_timeout=config.get("timeout", 15)
            )
            
            # Test connection with ping
            result = client.ping()
            response_time = (time.time() - start_time) * 1000
            
            client.close()
            
            return ServiceHealthStatus(
                name=config["name"],
                healthy=result,
                url=f"redis://{host}:{port}",
                port=port,
                response_time_ms=response_time,
                details={
                    "ping_result": result
                }
            )
            
        except redis.exceptions.ConnectionError:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=f"redis://{host}:{port}",
                port=port,
                error="Redis connection refused"
            )
        except redis.exceptions.TimeoutError:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=f"redis://{host}:{port}",
                port=port,
                error=f"Redis timeout after {config.get('timeout', 15)}s"
            )
        except Exception as e:
            return ServiceHealthStatus(
                name=config["name"],
                healthy=False,
                url=f"redis://{host}:{port}",
                port=port,
                error=str(e)
            )
            
    def get_service_urls(self) -> Dict[str, str]:
        """
        Get URLs for all configured services.
        
        Returns:
            Dictionary mapping service names to URLs
        """
        urls = {}
        
        for service_name, config in self.required_services.items():
            host = config["host"]
            port = config["port"]
            
            if config.get("type") == "http":
                urls[service_name] = f"http://{host}:{port}"
            elif config.get("type") == "database":
                username = self.env.get("POSTGRES_USER", "postgres")
                database = config.get("database", "netra_dev")
                urls[service_name] = f"postgresql://{username}@{host}:{port}/{database}"
            elif config.get("type") == "cache":
                urls[service_name] = f"redis://{host}:{port}"
                
        return urls
    
    def _save_port_config_for_cypress(self, service_statuses: Dict[str, Dict[str, Any]]):
        """
        Save discovered port configuration for Cypress to use.
        
        Args:
            service_statuses: Current service status information
        """
        try:
            # Get Cypress configuration from port discovery
            cypress_config = self.port_discovery.get_cypress_config()
            
            # Add service health status
            for service, status in service_statuses.items():
                cypress_config["env"][f"{service.upper()}_HEALTHY"] = status.get("healthy", False)
            
            # Save to .netra directory for Cypress to read
            config_dir = self.project_root / ".netra"
            config_dir.mkdir(exist_ok=True)
            
            config_file = config_dir / "cypress-ports.json"
            with open(config_file, 'w') as f:
                json.dump(cypress_config, f, indent=2)
                
            logger.info(f"Saved Cypress port configuration to {config_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save Cypress port configuration: {e}")