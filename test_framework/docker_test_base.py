"""
Docker Test Base Class - SSOT for Docker-based Integration Tests

This module provides the base class for all tests that require Docker services.
It follows SSOT principles and integrates with the unified Docker management system.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Testing Infrastructure  
- Business Goal: Provide reliable Docker test foundation
- Value Impact: Enables consistent Docker-based integration testing
- Strategic Impact: Prevents Docker configuration drift across test suites
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.ssot.docker import DockerTestUtility, DockerTestEnvironmentType
from shared.isolated_environment import get_env


class DockerTestBase(BaseIntegrationTest):
    """
    Base class for all Docker-based integration tests.
    
    Provides:
    - Unified Docker service management
    - Environment-specific configuration
    - Service health checking
    - Proper cleanup and teardown
    
    CRITICAL: This is the SSOT base class for Docker testing.
    All tests requiring Docker services MUST inherit from this class.
    """
    
    # Class-level Docker manager for efficient resource sharing
    _shared_docker_manager: Optional[UnifiedDockerManager] = None
    _docker_services_started: bool = False
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.setup_docker_environment()
        
    def teardown_method(self):
        """Tear down method called after each test method."""
        self.cleanup_docker_resources()
        super().teardown_method()
        
    def setup_docker_environment(self):
        """Initialize Docker environment for testing."""
        self.logger.info("Setting up Docker environment for test")
        
        # Initialize Docker utilities
        self.docker_utility = DockerTestUtility(
            environment_type=DockerTestEnvironmentType.INTEGRATION
        )
        
        # Get or create shared Docker manager
        if not self._shared_docker_manager:
            self._shared_docker_manager = UnifiedDockerManager(
                use_alpine=True,
                rebuild_images=True,
                rebuild_backend_only=True
            )
        
        self.docker_manager = self._shared_docker_manager
        
    async def start_required_services(self, services: List[str] = None) -> bool:
        """
        Start required Docker services for the test.
        
        Args:
            services: List of service names to start (defaults to all)
            
        Returns:
            True if all services started successfully
        """
        if services is None:
            services = ["postgres", "redis", "backend", "auth"]
            
        self.logger.info(f"Starting Docker services: {services}")
        
        try:
            # Start services using unified Docker manager
            success = await self.docker_manager.start_services(services)
            
            if success:
                # Wait for services to be healthy
                await self._wait_for_service_health(services)
                self._docker_services_started = True
                self.logger.info("All Docker services started successfully")
                return True
            else:
                self.logger.error("Failed to start Docker services")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Docker services: {e}")
            return False
            
    async def _wait_for_service_health(self, services: List[str], timeout: int = 60) -> bool:
        """
        Wait for services to be healthy.
        
        Args:
            services: List of service names to check
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all services are healthy
        """
        self.logger.info(f"Waiting for service health checks: {services}")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                health_status = await self.docker_manager.check_service_health(services)
                
                if all(health_status.values()):
                    self.logger.info("All services are healthy")
                    return True
                    
                # Log which services are not healthy yet
                unhealthy = [svc for svc, healthy in health_status.items() if not healthy]
                self.logger.debug(f"Services not yet healthy: {unhealthy}")
                
                await asyncio.sleep(2)  # Wait 2 seconds before next check
                
            except Exception as e:
                self.logger.warning(f"Health check error: {e}")
                await asyncio.sleep(2)
                
        self.logger.error(f"Service health check timeout after {timeout}s")
        return False
        
    def get_service_url(self, service: str, port: Optional[int] = None) -> str:
        """
        Get the URL for a Docker service.
        
        Args:
            service: Service name
            port: Optional specific port (uses service default if not provided)
            
        Returns:
            Service URL string
        """
        service_urls = {
            "postgres": "postgresql://test_user:test_password@localhost:5434/test_database",
            "redis": "redis://localhost:6381",
            "backend": "http://localhost:8000",
            "auth": "http://localhost:8081",
            "frontend": "http://localhost:3000"
        }
        
        if service in service_urls:
            base_url = service_urls[service]
            if port:
                # Replace port in URL if specific port provided
                import re
                base_url = re.sub(r':\d+', f':{port}', base_url)
            return base_url
            
        # Fallback for unknown services
        port = port or 8080
        return f"http://localhost:{port}"
        
    def cleanup_docker_resources(self):
        """Clean up Docker resources after test."""
        if self._docker_services_started:
            self.logger.info("Cleaning up Docker resources")
            try:
                # Note: We don't stop shared services as other tests may be using them
                # The unified Docker manager handles cleanup at the end of test runs
                pass
            except Exception as e:
                self.logger.error(f"Error during Docker cleanup: {e}")
                
    @pytest.fixture(autouse=True)
    def docker_services(self):
        """Pytest fixture to ensure Docker services are available."""
        # This fixture runs automatically for all tests inheriting from DockerTestBase
        if not self._docker_services_started:
            # Start services synchronously for pytest compatibility
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            success = loop.run_until_complete(self.start_required_services())
            
            if not success:
                pytest.skip("Docker services could not be started")
                
        yield
        
        # Cleanup is handled in teardown_method
        
    def assert_service_available(self, service: str, timeout: int = 30) -> bool:
        """
        Assert that a service is available and responding.
        
        Args:
            service: Service name to check
            timeout: Maximum time to wait
            
        Returns:
            True if service is available
            
        Raises:
            AssertionError: If service is not available
        """
        import httpx
        import socket
        
        service_url = self.get_service_url(service)
        
        if service == "postgres":
            # Check PostgreSQL connection
            try:
                import psycopg2
                conn = psycopg2.connect(service_url)
                conn.close()
                return True
            except Exception as e:
                raise AssertionError(f"PostgreSQL not available: {e}")
                
        elif service == "redis":
            # Check Redis connection
            try:
                import redis
                r = redis.from_url(service_url)
                r.ping()
                return True
            except Exception as e:
                raise AssertionError(f"Redis not available: {e}")
                
        else:
            # Check HTTP services
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.get(f"{service_url}/health", timeout=timeout)
                    assert response.status_code == 200
                    return True
            except Exception as e:
                raise AssertionError(f"Service {service} not available: {e}")
                
    @classmethod
    def setup_class(cls):
        """Set up class-level resources."""
        cls.logger = logging.getLogger(cls.__name__)
        
    @classmethod  
    def teardown_class(cls):
        """Clean up class-level resources."""
        if cls._shared_docker_manager:
            # Allow some time for cleanup
            try:
                # The unified Docker manager handles proper cleanup
                pass
            except Exception as e:
                cls.logger.error(f"Error in class teardown: {e}")


class PostgreSQLDockerTestBase(DockerTestBase):
    """Specialized base class for tests requiring PostgreSQL."""
    
    async def start_required_services(self, services: List[str] = None) -> bool:
        """Start PostgreSQL and dependent services."""
        if services is None:
            services = ["postgres"]
        return await super().start_required_services(services)
        
    def get_postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string for tests."""
        return self.get_service_url("postgres")


class RedisDockerTestBase(DockerTestBase):
    """Specialized base class for tests requiring Redis."""
    
    async def start_required_services(self, services: List[str] = None) -> bool:
        """Start Redis and dependent services."""
        if services is None:
            services = ["redis"]
        return await super().start_required_services(services)
        
    def get_redis_url(self) -> str:
        """Get Redis URL for tests."""
        return self.get_service_url("redis")


class FullStackDockerTestBase(DockerTestBase):
    """Specialized base class for full-stack integration tests."""
    
    async def start_required_services(self, services: List[str] = None) -> bool:
        """Start all services for full-stack testing."""
        if services is None:
            services = ["postgres", "redis", "backend", "auth", "frontend"]
        return await super().start_required_services(services)


# Export the main classes
__all__ = [
    "DockerTestBase",
    "PostgreSQLDockerTestBase", 
    "RedisDockerTestBase",
    "FullStackDockerTestBase"
]