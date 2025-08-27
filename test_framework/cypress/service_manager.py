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
from dev_launcher.isolated_environment import get_env

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
        
        # Service configuration
        self.required_services = self._get_required_services()
        
    def _get_required_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration for all required services.
        
        Returns:
            Service configuration dictionary
        """
        return {
            "backend": {
                "name": "Netra Backend",
                "type": "http",
                "host": "localhost",
                "port": 8000,
                "health_endpoint": "/api/health",
                "timeout": 30,
                "required": True
            },
            "frontend": {
                "name": "Frontend Dev Server",
                "type": "http", 
                "host": "localhost",
                "port": 3000,
                "health_endpoint": "/",
                "timeout": 30,
                "required": True
            },
            "postgres": {
                "name": "PostgreSQL Database",
                "type": "database",
                "host": "localhost",
                "port": 5432,
                "database": "netra_dev",
                "timeout": 30,
                "required": True,
                "docker_fallback": True
            },
            "redis": {
                "name": "Redis Cache",
                "type": "cache",
                "host": "localhost",
                "port": 6379,
                "timeout": 15,
                "required": True,
                "docker_fallback": True
            }
        }
        
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
        
        # Start Docker services if needed
        await self._start_docker_services_if_needed()
        
        # Check each service
        for service_name, config in self.required_services.items():
            logger.info(f"Checking service: {service_name}")
            
            remaining_timeout = max(0, timeout - int(time.time() - start_time))
            status = await self._ensure_service_ready(service_name, config, remaining_timeout)
            service_statuses[service_name] = status
            
            if config.get("required", True) and not status["healthy"]:
                logger.error(f"Required service {service_name} is not healthy")
                
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