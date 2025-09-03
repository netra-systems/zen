"""
Dynamic Port Allocation for Podman Testing

Provides dynamic port allocation for Podman containers to avoid conflicts
and enable parallel test execution.
"""

import socket
import random
import logging
import subprocess
import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class PodmanDynamicPortManager:
    """Manages dynamic port allocation for Podman containers."""
    
    # Port ranges for different services
    PORT_RANGES = {
        'postgres': (30000, 30099),
        'redis': (30100, 30199),
        'clickhouse': (30200, 30299),
        'backend': (30300, 30399),
        'auth': (30400, 30499),
        'frontend': (30500, 30599),
    }
    
    def __init__(self, test_id: str):
        """Initialize with a test ID for container naming."""
        self.test_id = test_id
        self.allocated_ports: Dict[str, int] = {}
        self.running_containers: List[str] = []
        
    def find_free_port(self, start: int, end: int) -> Optional[int]:
        """Find a free port in the given range."""
        # Try random ports first for better distribution
        for _ in range(10):
            port = random.randint(start, end)
            if self.is_port_free(port):
                return port
        
        # Fall back to sequential search
        for port in range(start, end + 1):
            if self.is_port_free(port):
                return port
        
        return None
    
    def is_port_free(self, port: int) -> bool:
        """Check if a port is free."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex(('127.0.0.1', port))
                return result != 0
        except Exception:
            return False
    
    def allocate_ports(self) -> Dict[str, int]:
        """Allocate dynamic ports for all services."""
        for service, (start, end) in self.PORT_RANGES.items():
            port = self.find_free_port(start, end)
            if not port:
                raise RuntimeError(f"No free ports available for {service} in range {start}-{end}")
            self.allocated_ports[service] = port
            logger.info(f"Allocated port {port} for {service}")
        
        return self.allocated_ports.copy()
    
    def start_postgres(self, port: Optional[int] = None) -> Tuple[bool, str]:
        """Start PostgreSQL container with dynamic port."""
        if port is None:
            port = self.allocated_ports.get('postgres')
            if not port:
                port = self.find_free_port(*self.PORT_RANGES['postgres'])
                self.allocated_ports['postgres'] = port
        
        container_name = f"test-postgres-{self.test_id}"
        
        try:
            # Stop existing container if it exists
            subprocess.run(
                ["podman", "stop", container_name],
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ["podman", "rm", container_name],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # Container doesn't exist
        
        # Start new container
        cmd = [
            "podman", "run", "-d",
            "--name", container_name,
            "-e", "POSTGRES_USER=test",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=netra_test",
            "-e", "POSTGRES_HOST_AUTH_METHOD=md5",
            "-p", f"{port}:5432",
            "docker.io/postgres:15-alpine"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            self.running_containers.append(container_name)
            logger.info(f"Started PostgreSQL on port {port}")
            return True, container_name
        else:
            logger.error(f"Failed to start PostgreSQL: {result.stderr}")
            return False, result.stderr
    
    def start_redis(self, port: Optional[int] = None) -> Tuple[bool, str]:
        """Start Redis container with dynamic port."""
        if port is None:
            port = self.allocated_ports.get('redis')
            if not port:
                port = self.find_free_port(*self.PORT_RANGES['redis'])
                self.allocated_ports['redis'] = port
        
        container_name = f"test-redis-{self.test_id}"
        
        try:
            # Stop existing container if it exists
            subprocess.run(
                ["podman", "stop", container_name],
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ["podman", "rm", container_name],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # Container doesn't exist
        
        # Start new container
        cmd = [
            "podman", "run", "-d",
            "--name", container_name,
            "-p", f"{port}:6379",
            "docker.io/redis:7-alpine",
            "redis-server",
            "--maxmemory", "64mb",
            "--maxmemory-policy", "allkeys-lru"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            self.running_containers.append(container_name)
            logger.info(f"Started Redis on port {port}")
            return True, container_name
        else:
            logger.error(f"Failed to start Redis: {result.stderr}")
            return False, result.stderr
    
    def start_clickhouse(self, port: Optional[int] = None) -> Tuple[bool, str]:
        """Start ClickHouse container with dynamic port."""
        if port is None:
            port = self.allocated_ports.get('clickhouse')
            if not port:
                port = self.find_free_port(*self.PORT_RANGES['clickhouse'])
                self.allocated_ports['clickhouse'] = port
        
        container_name = f"test-clickhouse-{self.test_id}"
        
        try:
            # Stop existing container if it exists
            subprocess.run(
                ["podman", "stop", container_name],
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ["podman", "rm", container_name],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # Container doesn't exist
        
        # Start new container
        cmd = [
            "podman", "run", "-d",
            "--name", container_name,
            "-e", "CLICKHOUSE_DB=netra_test_analytics",
            "-e", "CLICKHOUSE_USER=test",
            "-e", "CLICKHOUSE_PASSWORD=test",
            "-e", "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1",
            "-p", f"{port}:8123",
            "-p", f"{port + 1}:9000",
            "docker.io/clickhouse/clickhouse-server:23.8"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            self.running_containers.append(container_name)
            logger.info(f"Started ClickHouse on ports {port} (HTTP) and {port + 1} (TCP)")
            return True, container_name
        else:
            logger.error(f"Failed to start ClickHouse: {result.stderr}")
            return False, result.stderr
    
    def wait_for_postgres(self, container_name: str, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["podman", "exec", container_name, "pg_isready", "-U", "test"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"PostgreSQL {container_name} is ready")
                    return True
            except Exception:
                pass
            
            time.sleep(1)
        
        logger.warning(f"PostgreSQL {container_name} not ready after {timeout}s")
        return False
    
    def wait_for_redis(self, container_name: str, timeout: int = 30) -> bool:
        """Wait for Redis to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["podman", "exec", container_name, "redis-cli", "ping"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and b"PONG" in result.stdout:
                    logger.info(f"Redis {container_name} is ready")
                    return True
            except Exception:
                pass
            
            time.sleep(1)
        
        logger.warning(f"Redis {container_name} not ready after {timeout}s")
        return False
    
    def start_all_services(self) -> Dict[str, int]:
        """Start all test services with dynamic ports."""
        # Allocate ports
        self.allocate_ports()
        
        # Start PostgreSQL
        success, pg_container = self.start_postgres()
        if not success:
            raise RuntimeError(f"Failed to start PostgreSQL: {pg_container}")
        
        # Start Redis
        success, redis_container = self.start_redis()
        if not success:
            raise RuntimeError(f"Failed to start Redis: {redis_container}")
        
        # Wait for services to be ready
        if not self.wait_for_postgres(f"test-postgres-{self.test_id}"):
            raise RuntimeError("PostgreSQL did not become ready")
        
        if not self.wait_for_redis(f"test-redis-{self.test_id}"):
            raise RuntimeError("Redis did not become ready")
        
        logger.info(f"All services started with ports: {self.allocated_ports}")
        return self.allocated_ports.copy()
    
    def cleanup(self):
        """Stop and remove all containers."""
        for container in self.running_containers:
            try:
                subprocess.run(
                    ["podman", "stop", container],
                    capture_output=True,
                    timeout=10
                )
                subprocess.run(
                    ["podman", "rm", container],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"Cleaned up container {container}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {container}: {e}")
        
        self.running_containers.clear()
        self.allocated_ports.clear()