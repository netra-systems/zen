"""Service dependency manager for Cypress testing.

This module manages service dependencies required for Cypress E2E tests,
ensuring all required services are available before running tests.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
import subprocess
import time
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class ServiceDependencyManager:
    """Manages service dependencies for Cypress tests."""
    
    def __init__(self):
        """Initialize service dependency manager."""
        self.env = get_env()
        self.required_services = self._get_required_services()
        self.service_health = {}
        self.retry_count = 3
        self.timeout = 30
    
    def _get_required_services(self) -> Dict[str, Dict]:
        """Get required services configuration.
        
        Returns:
            Dictionary of service names and their configurations
        """
        return {
            "backend": {
                "url": self.env.get("TEST_BACKEND_URL", "http://localhost:8000"),
                "health_endpoint": "/health",
                "required": True
            },
            "frontend": {
                "url": self.env.get("TEST_FRONTEND_URL", "http://localhost:3000"),
                "health_endpoint": "/",
                "required": True
            },
            "auth": {
                "url": self.env.get("TEST_AUTH_URL", "http://localhost:8081"),
                "health_endpoint": "/health",
                "required": False
            },
            "database": {
                "host": self.env.get("TEST_DB_HOST", "localhost"),
                "port": int(self.env.get("TEST_DB_PORT", "5434")),
                "required": True
            },
            "redis": {
                "host": self.env.get("TEST_REDIS_HOST", "localhost"),
                "port": int(self.env.get("TEST_REDIS_PORT", "6381")),
                "required": False
            }
        }
    
    async def check_service_health(self, service_name: str, config: Dict) -> bool:
        """Check if a service is healthy.
        
        Args:
            service_name: Name of the service to check
            config: Service configuration
            
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if "url" in config:
                # HTTP service - check via health endpoint
                import aiohttp
                url = config["url"] + config.get("health_endpoint", "/health")
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        return response.status == 200
                        
            elif "host" in config and "port" in config:
                # TCP service - check port connectivity
                future = asyncio.open_connection(config["host"], config["port"])
                reader, writer = await asyncio.wait_for(future, timeout=5)
                writer.close()
                await writer.wait_closed()
                return True
                
        except Exception as e:
            logger.debug(f"Service {service_name} health check failed: {e}")
            return False
        
        return False
    
    async def wait_for_services(self) -> bool:
        """Wait for all required services to become available.
        
        Returns:
            True if all required services are available, False otherwise
        """
        logger.info("Checking service dependencies for Cypress tests...")
        
        for attempt in range(self.retry_count):
            all_healthy = True
            
            for service_name, config in self.required_services.items():
                if not config.get("required", True):
                    continue
                
                is_healthy = await self.check_service_health(service_name, config)
                self.service_health[service_name] = is_healthy
                
                if not is_healthy:
                    logger.warning(f"Service {service_name} is not healthy (attempt {attempt + 1}/{self.retry_count})")
                    all_healthy = False
                else:
                    logger.debug(f"Service {service_name} is healthy")
            
            if all_healthy:
                logger.info("All required services are healthy")
                return True
            
            if attempt < self.retry_count - 1:
                logger.info(f"Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
        
        logger.error("Not all required services are available after retries")
        self._log_service_status()
        return False
    
    def _log_service_status(self):
        """Log the status of all services."""
        logger.info("Service status summary:")
        for service_name, is_healthy in self.service_health.items():
            status = "[U+2713] HEALTHY" if is_healthy else "[U+2717] UNHEALTHY"
            required = "REQUIRED" if self.required_services[service_name].get("required", True) else "OPTIONAL"
            logger.info(f"  {service_name}: {status} ({required})")
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy required services.
        
        Returns:
            List of service names that are unhealthy
        """
        unhealthy = []
        for service_name, is_healthy in self.service_health.items():
            config = self.required_services[service_name]
            if not is_healthy and config.get("required", True):
                unhealthy.append(service_name)
        return unhealthy
    
    def start_missing_services(self) -> bool:
        """Attempt to start missing services using Docker.
        
        Returns:
            True if services were started successfully, False otherwise
        """
        unhealthy_services = self.get_unhealthy_services()
        
        if not unhealthy_services:
            return True
        
        logger.info(f"Attempting to start missing services: {unhealthy_services}")
        
        try:
            # Try to start services using docker-compose
            cmd = ["docker-compose", "up", "-d"] + unhealthy_services
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Services started successfully via docker-compose")
                return True
            else:
                logger.warning(f"Failed to start services: {result.stderr}")
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Could not start services via docker-compose: {e}")
        
        return False
    
    async def ensure_services_ready(self) -> bool:
        """Ensure all required services are ready for testing.
        
        Returns:
            True if all services are ready, False otherwise
        """
        # First check if services are already running
        if await self.wait_for_services():
            return True
        
        # Try to start missing services
        if self.start_missing_services():
            # Wait a bit for services to initialize
            await asyncio.sleep(10)
            
            # Check again
            return await self.wait_for_services()
        
        return False
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for all HTTP services.
        
        Returns:
            Dictionary mapping service names to their URLs
        """
        urls = {}
        for service_name, config in self.required_services.items():
            if "url" in config:
                urls[service_name] = config["url"]
        return urls