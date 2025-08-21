"""
L3-7: Circuit Breaker with Real Service Failures Integration Test

BVJ: Circuit breaker protection prevents cascading failures and ensures platform 
stability during service degradation, critical for maintaining SLA compliance.

Tests circuit breaker behavior with real service failures using Docker containers.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from typing import Any, Dict

import aiohttp
import docker
import pytest

from netra_backend.app.services.external_service_client import ExternalServiceClient

# Add project root to path
from netra_backend.app.utils.circuit_breaker import CircuitBreaker

# Add project root to path


@pytest.mark.L3
class TestCircuitBreakerServiceFailuresL3:
    """Test circuit breaker with real service failures."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def failing_service_container(self, docker_client):
        """Start a container that can simulate service failures."""
        container = docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name="circuit_breaker_test_service"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
        
        # Wait for service to be ready
        await self._wait_for_service(f"http://localhost:{port}")
        
        yield f"http://localhost:{port}"
        
        container.stop()
        container.remove()
    
    async def _wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=1)) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Service at {url} not ready within {timeout}s")
    
    def _stop_service_container(self, docker_client, container_name: str):
        """Stop service container to simulate failure."""
        try:
            container = docker_client.containers.get(container_name)
            container.stop()
        except docker.errors.NotFound:
            pass
    
    def _start_service_container(self, docker_client, container_name: str):
        """Start service container to simulate recovery."""
        try:
            container = docker_client.containers.get(container_name)
            container.start()
        except docker.errors.NotFound:
            pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(
        self, 
        docker_client, 
        failing_service_container
    ):
        """Test that circuit breaker opens after consecutive failures."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=5.0,
            recovery_timeout=10.0
        )
        
        client = ExternalServiceClient(
            base_url=failing_service_container,
            circuit_breaker=circuit_breaker
        )
        
        # Stop the service to cause failures
        self._stop_service_container(docker_client, "circuit_breaker_test_service")
        
        # Generate failures to trip circuit breaker
        failure_count = 0
        for i in range(5):
            try:
                await client.make_request("/health")
            except Exception:
                failure_count += 1
        
        assert failure_count >= 3
        assert circuit_breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(
        self, 
        docker_client, 
        failing_service_container
    ):
        """Test circuit breaker half-open state and recovery."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout=2.0,
            recovery_timeout=3.0
        )
        
        client = ExternalServiceClient(
            base_url=failing_service_container,
            circuit_breaker=circuit_breaker
        )
        
        # Trip circuit breaker
        self._stop_service_container(docker_client, "circuit_breaker_test_service")
        
        for _ in range(3):
            try:
                await client.make_request("/health")
            except:
                pass
        
        assert circuit_breaker.state == "open"
        
        # Wait for recovery timeout
        await asyncio.sleep(3.5)
        
        # Restart service
        self._start_service_container(docker_client, "circuit_breaker_test_service")
        await self._wait_for_service(failing_service_container)
        
        # Circuit breaker should be half-open
        assert circuit_breaker.state == "half_open"
        
        # Successful request should close circuit
        response = await client.make_request("/")
        assert response is not None
        assert circuit_breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_collection(
        self, 
        docker_client, 
        failing_service_container
    ):
        """Test that circuit breaker collects proper metrics."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout=1.0,
            recovery_timeout=2.0,
            enable_metrics=True
        )
        
        client = ExternalServiceClient(
            base_url=failing_service_container,
            circuit_breaker=circuit_breaker
        )
        
        # Generate mix of success and failures
        self._stop_service_container(docker_client, "circuit_breaker_test_service")
        
        # Cause failures
        for _ in range(3):
            try:
                await client.make_request("/health")
            except:
                pass
        
        metrics = circuit_breaker.get_metrics()
        assert metrics["total_requests"] >= 3
        assert metrics["failed_requests"] >= 2
        assert metrics["circuit_opened_count"] >= 1
        assert metrics["state"] == "open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_timeout_failures(
        self, 
        docker_client, 
        failing_service_container
    ):
        """Test circuit breaker behavior with timeout failures."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout=0.1,  # Very short timeout
            recovery_timeout=2.0
        )
        
        client = ExternalServiceClient(
            base_url=failing_service_container,
            circuit_breaker=circuit_breaker,
            request_timeout=0.05  # Even shorter request timeout
        )
        
        # Even with service running, timeouts should trip breaker
        timeout_failures = 0
        for _ in range(4):
            try:
                await client.make_request("/")
            except asyncio.TimeoutError:
                timeout_failures += 1
            except:
                pass
        
        assert timeout_failures >= 2
        assert circuit_breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_requests(
        self, 
        docker_client, 
        failing_service_container
    ):
        """Test circuit breaker with concurrent requests during failures."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=1.0,
            recovery_timeout=3.0
        )
        
        client = ExternalServiceClient(
            base_url=failing_service_container,
            circuit_breaker=circuit_breaker
        )
        
        # Stop service
        self._stop_service_container(docker_client, "circuit_breaker_test_service")
        
        # Make concurrent requests
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(self._safe_request(client, "/health"))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most requests should fail
        failures = sum(1 for r in results if isinstance(r, Exception))
        assert failures >= 8
        assert circuit_breaker.state == "open"
    
    async def _safe_request(self, client, path: str):
        """Make a safe request that handles exceptions."""
        try:
            return await client.make_request(path)
        except Exception as e:
            return e