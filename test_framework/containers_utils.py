"""
Testcontainers utility module for L3 integration tests.

This module provides shared container management utilities for L3 tests
that require real containerized services according to the testing specification.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Tuple

from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

logger = logging.getLogger(__name__)


class ContainerHelper:
    """Helper class for managing testcontainers in L3 integration tests."""
    
    __test__ = False  # Tell pytest this is not a test class
    
    def __init__(self):
        self.active_containers: Dict[str, Any] = {}
        self.container_urls: Dict[str, str] = {}
    
    def start_postgres_container(
        self, 
        image: str = "postgres:17.6-alpine",
        database: str = "test_db",
        username: str = "test_user",
        password: str = "test_password"
    ) -> Tuple[PostgresContainer, str]:
        """
        Start a PostgreSQL container for testing.
        
        Returns:
            Tuple of (container instance, connection URL)
        """
        try:
            container = PostgresContainer(
                image=image,
                dbname=database,
                user=username,
                password=password
            )
            container.start()
            
            # Get connection URL and convert to async format
            connection_url = container.get_connection_url()
            async_url = connection_url.replace("postgresql://", "postgresql+asyncpg://")
            
            self.active_containers["postgres"] = container
            self.container_urls["postgres"] = async_url
            
            logger.info(f"Started PostgreSQL container: {async_url}")
            return container, async_url
            
        except Exception as e:
            logger.error(f"Failed to start PostgreSQL container: {e}")
            raise
    
    def start_redis_container(
        self,
        image: str = "redis:7-alpine"
    ) -> Tuple[RedisContainer, str]:
        """
        Start a Redis container for testing.
        
        Returns:
            Tuple of (container instance, connection URL)
        """
        try:
            container = RedisContainer(image=image)
            container.start()
            
            # Get connection details
            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)
            connection_url = f"redis://{host}:{port}"
            
            self.active_containers["redis"] = container
            self.container_urls["redis"] = connection_url
            
            logger.info(f"Started Redis container: {connection_url}")
            return container, connection_url
            
        except Exception as e:
            logger.error(f"Failed to start Redis container: {e}")
            raise
    
    def start_clickhouse_container(
        self,
        image: str = "clickhouse/clickhouse-server:latest"
    ) -> Tuple[Any, str]:
        """
        Start a ClickHouse container for testing.
        
        Note: This uses a generic container approach since testcontainers
        doesn't have a dedicated ClickHouse container yet.
        
        Returns:
            Tuple of (container instance, connection URL)
        """
        try:
            from testcontainers.generic import GenericContainer
            
            container = GenericContainer(image)
            container.with_exposed_ports(8123, 9000)  # HTTP and Native ports
            container.with_env("CLICKHOUSE_DB", "test_db")
            container.with_env("CLICKHOUSE_USER", "test_user")
            container.with_env("CLICKHOUSE_PASSWORD", "test_password")
            container.start()
            
            # Get connection details
            host = container.get_container_host_ip()
            http_port = container.get_exposed_port(8123)
            native_port = container.get_exposed_port(9000)
            
            http_url = f"http://{host}:{http_port}"
            native_url = f"clickhouse://{host}:{native_port}/test_db"
            
            self.active_containers["clickhouse"] = container
            self.container_urls["clickhouse_http"] = http_url
            self.container_urls["clickhouse_native"] = native_url
            
            logger.info(f"Started ClickHouse container - HTTP: {http_url}, Native: {native_url}")
            return container, native_url
            
        except Exception as e:
            logger.error(f"Failed to start ClickHouse container: {e}")
            raise
    
    @asynccontextmanager
    async def postgres_container(self, **kwargs):
        """
        Async context manager for PostgreSQL container.
        
        Usage:
            async with helper.postgres_container() as (container, url):
                # Use the container
                pass
        """
        container, url = self.start_postgres_container(**kwargs)
        try:
            yield container, url
        finally:
            self.stop_container("postgres")
    
    @asynccontextmanager
    async def redis_container(self, **kwargs):
        """
        Async context manager for Redis container.
        
        Usage:
            async with helper.redis_container() as (container, url):
                # Use the container
                pass
        """
        container, url = self.start_redis_container(**kwargs)
        try:
            yield container, url
        finally:
            self.stop_container("redis")
    
    def stop_container(self, container_name: str) -> None:
        """Stop a specific container by name."""
        if container_name in self.active_containers:
            try:
                container = self.active_containers[container_name]
                container.stop()
                del self.active_containers[container_name]
                if container_name in self.container_urls:
                    del self.container_urls[container_name]
                logger.info(f"Stopped {container_name} container")
            except Exception as e:
                logger.warning(f"Error stopping {container_name} container: {e}")
    
    def stop_all_containers(self) -> None:
        """Stop all active containers."""
        for container_name in list(self.active_containers.keys()):
            self.stop_container(container_name)
    
    def get_container_url(self, container_name: str) -> Optional[str]:
        """Get the connection URL for a specific container."""
        return self.container_urls.get(container_name)
    
    def wait_for_container_ready(
        self, 
        container_name: str, 
        max_wait_seconds: int = 30
    ) -> bool:
        """
        Wait for a container to be ready for connections.
        
        Args:
            container_name: Name of the container to wait for
            max_wait_seconds: Maximum time to wait
            
        Returns:
            True if container is ready, False if timeout
        """
        if container_name not in self.active_containers:
            return False
        
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            try:
                container = self.active_containers[container_name]
                
                # Basic readiness check - try to get container info
                if hasattr(container, 'get_container_host_ip'):
                    container.get_container_host_ip()
                    return True
                    
            except Exception:
                time.sleep(1)
                continue
        
        logger.warning(f"Container {container_name} not ready after {max_wait_seconds}s")
        return False


def create_test_database_containers() -> ContainerHelper:
    """
    Factory function to create and start database containers for testing.
    
    Returns:
        Configured ContainerHelper with active containers
    """
    helper = ContainerHelper()
    
    # Start PostgreSQL container
    helper.start_postgres_container()
    
    # Start Redis container  
    helper.start_redis_container()
    
    return helper


def get_test_postgres_url() -> str:
    """
    Get a PostgreSQL URL for testing.
    
    This function can be used when you need a quick PostgreSQL URL
    without managing the container lifecycle yourself.
    """
    helper = ContainerHelper()
    _, url = helper.start_postgres_container()
    return url


def get_test_redis_url() -> str:
    """
    Get a Redis URL for testing.
    
    This function can be used when you need a quick Redis URL
    without managing the container lifecycle yourself.
    """
    helper = ContainerHelper()
    _, url = helper.start_redis_container()
    return url