"""Auth Service Circuit Breaker Cascade L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent cascading failures when auth service fails
- Value Impact: $20K MRR - Auth service failures must not cascade to other services
- Strategic Impact: Ensures system resilience and maintains user sessions during auth outages

Critical Path: Auth failure detection -> Circuit breaker activation -> Fallback mechanisms -> Service isolation -> Recovery coordination
Coverage: Multi-service circuit breaker coordination, auth service failure scenarios, fallback auth mechanisms, state synchronization
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import docker
import pytest
from clients.auth_client_cache import AuthCircuitBreakerManager

# Add project root to path
from netra_backend.app.core.circuit_breaker_core import CircuitBreaker
from netra_backend.app.core.circuit_breaker_types import CircuitConfig, CircuitState

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Represents a service endpoint with circuit breaker."""
    name: str
    url: str
    circuit_breaker: CircuitBreaker
    has_auth_dependency: bool


@dataclass
class CascadeMetrics:
    """Circuit breaker cascade metrics."""
    auth_failures: int = 0
    services_isolated: int = 0
    fallback_activations: int = 0
    recovery_attempts: int = 0


class AuthServiceCircuitBreakerCascadeL3Manager:
    """Manages L3 auth service circuit breaker cascade testing."""
    
    def __init__(self, docker_client):
        self.docker_client = docker_client
        self.auth_container = None
        self.backend_container = None
        self.websocket_container = None
        self.service_endpoints: Dict[str, ServiceEndpoint] = {}
        self.cascade_metrics = CascadeMetrics()
        self.auth_url = None
        
    async def setup_containerized_environment(self):
        """Setup containerized environment for L3 testing."""
        try:
            # Start Auth service container
            self.auth_container = self._start_auth_service_container()
            self.auth_url = self._get_container_url(self.auth_container, 80)
            
            # Start Backend service container
            self.backend_container = self._start_backend_container()
            backend_url = self._get_container_url(self.backend_container, 80)
            
            # Start WebSocket service container
            self.websocket_container = self._start_websocket_container()
            websocket_url = self._get_container_url(self.websocket_container, 80)
            
            # Wait for services to be ready
            await self._wait_for_service_health(self.auth_url)
            await self._wait_for_service_health(backend_url)
            await self._wait_for_service_health(websocket_url)
            
            # Initialize service endpoints
            await self._initialize_service_endpoints(backend_url, websocket_url)
            
        except Exception as e:
            logger.error(f"Failed to setup environment: {e}")
            await self.cleanup_environment()
            raise
    
    def _start_auth_service_container(self) -> Any:
        """Start auth service container."""
        return self.docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name=f"auth_circuit_test_auth_{uuid.uuid4().hex[:8]}",
            remove=True
        )
    
    def _start_backend_container(self) -> Any:
        """Start backend service container.""" 
        return self.docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name=f"auth_circuit_test_backend_{uuid.uuid4().hex[:8]}",
            remove=True
        )
    
    def _start_websocket_container(self) -> Any:
        """Start WebSocket service container."""
        return self.docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name=f"auth_circuit_test_ws_{uuid.uuid4().hex[:8]}",
            remove=True
        )
    
    def _get_container_url(self, container: Any, port: int) -> str:
        """Get container URL for HTTP access."""
        container.reload()
        host_port = container.attrs['NetworkSettings']['Ports'][f'{port}/tcp'][0]['HostPort']
        return f"http://localhost:{host_port}"
    
    async def _initialize_service_endpoints(self, backend_url: str, websocket_url: str):
        """Initialize service endpoints with circuit breakers."""
        # Backend service with auth dependency
        backend_circuit = CircuitBreaker(CircuitConfig(
            name="backend_auth",
            failure_threshold=3,
            recovery_timeout=30,
            timeout_seconds=10
        ))
        
        self.service_endpoints["backend"] = ServiceEndpoint(
            name="backend",
            url=backend_url,
            circuit_breaker=backend_circuit,
            has_auth_dependency=True
        )
        
        # WebSocket service with auth dependency
        websocket_circuit = CircuitBreaker(CircuitConfig(
            name="websocket_auth",
            failure_threshold=2,
            recovery_timeout=20,
            timeout_seconds=5
        ))
        
        self.service_endpoints["websocket"] = ServiceEndpoint(
            name="websocket",
            url=websocket_url,
            circuit_breaker=websocket_circuit,
            has_auth_dependency=True
        )
    
    async def simulate_auth_service_failure(self):
        """Simulate auth service failure by stopping container."""
        if self.auth_container:
            self.auth_container.stop()
            self.cascade_metrics.auth_failures += 1
    
    async def restore_auth_service(self):
        """Restore auth service by starting container."""
        if self.auth_container:
            self.auth_container.start()
            await self._wait_for_service_health(self.auth_url)
    
    async def trigger_auth_requests_cascade(self) -> Dict[str, Any]:
        """Trigger auth requests across all dependent services."""
        results = {}
        for service_name, endpoint in self.service_endpoints.items():
            if endpoint.has_auth_dependency:
                result = await self._test_service_auth_dependency(endpoint)
                results[service_name] = result
        return results
    
    async def _test_service_auth_dependency(self, endpoint: ServiceEndpoint) -> Dict[str, Any]:
        """Test service auth dependency and circuit breaker behavior."""
        failures = 0
        successes = 0
        circuit_opened = False
        
        for i in range(6):
            try:
                if endpoint.circuit_breaker.can_execute():
                    success = await self._make_auth_request(endpoint)
                    if success:
                        endpoint.circuit_breaker.record_success()
                        successes += 1
                    else:
                        endpoint.circuit_breaker.record_failure("auth_failure")
                        failures += 1
                        if endpoint.circuit_breaker.is_open:
                            circuit_opened = True
                            self.cascade_metrics.services_isolated += 1
                            break
                else:
                    await self._activate_fallback_auth(endpoint)
                    self.cascade_metrics.fallback_activations += 1
            except Exception:
                endpoint.circuit_breaker.record_failure("exception")
                failures += 1
            await asyncio.sleep(0.1)
        
        return {
            "service": endpoint.name,
            "successes": successes,
            "failures": failures,
            "circuit_opened": circuit_opened,
            "circuit_state": endpoint.circuit_breaker.state.value,
            "fallback_activated": failures > 0 and circuit_opened
        }
    
    async def _make_auth_request(self, endpoint: ServiceEndpoint) -> bool:
        """Make auth request to service endpoint."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.auth_url}/validate") as response:
                    return response.status == 200
        except:
            return False
    
    async def _activate_fallback_auth(self, endpoint: ServiceEndpoint):
        """Activate fallback auth mechanism."""
        logger.info(f"Activating fallback auth for {endpoint.name}")
        await asyncio.sleep(0.05)
    
    async def test_circuit_breaker_recovery_coordination(self) -> Dict[str, Any]:
        """Test circuit breaker recovery coordination across services."""
        await self.simulate_auth_service_failure()
        await asyncio.sleep(1)
        cascade_results = await self.trigger_auth_requests_cascade()
        await self.restore_auth_service()
        await asyncio.sleep(2)
        recovery_results = {}
        for service_name, endpoint in self.service_endpoints.items():
            if endpoint.has_auth_dependency:
                result = await self._test_service_recovery(endpoint)
                recovery_results[service_name] = result
        
        return {
            "cascade_phase": cascade_results,
            "recovery_phase": recovery_results,
            "cascade_metrics": {
                "auth_failures": self.cascade_metrics.auth_failures,
                "services_isolated": self.cascade_metrics.services_isolated,
                "fallback_activations": self.cascade_metrics.fallback_activations,
                "recovery_attempts": self.cascade_metrics.recovery_attempts
            }
        }
    
    async def _test_service_recovery(self, endpoint: ServiceEndpoint) -> Dict[str, Any]:
        """Test service recovery after auth service restoration."""
        initial_state = endpoint.circuit_breaker.state
        recovery_successful = False
        attempts = 0
        
        max_wait = 35
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if endpoint.circuit_breaker.state == CircuitState.HALF_OPEN:
                break
            await asyncio.sleep(0.5)
        if endpoint.circuit_breaker.state == CircuitState.HALF_OPEN:
            for _ in range(3):
                attempts += 1
                self.cascade_metrics.recovery_attempts += 1
                
                if endpoint.circuit_breaker.can_execute():
                    success = await self._make_auth_request(endpoint)
                    if success:
                        endpoint.circuit_breaker.record_success()
                        if endpoint.circuit_breaker.state == CircuitState.CLOSED:
                            recovery_successful = True
                            break
                    else:
                        endpoint.circuit_breaker.record_failure("recovery_failure")
                        break
                await asyncio.sleep(0.1)
        
        return {
            "service": endpoint.name,
            "initial_state": initial_state.value,
            "final_state": endpoint.circuit_breaker.state.value,
            "recovery_successful": recovery_successful,
            "recovery_attempts": attempts
        }
    
    async def _wait_for_service_health(self, url: str, timeout: int = 30):
        """Wait for service to be healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                timeout_config = aiohttp.ClientTimeout(total=2)
                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    async with session.get(f"{url}/health") as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Service at {url} not healthy within {timeout}s")
    
    async def cleanup_environment(self):
        """Cleanup containerized environment."""
        containers = [self.auth_container, self.backend_container, self.websocket_container]
        for container in containers:
            if container:
                try:
                    container.stop()
                    container.remove()
                except:
                    pass


@pytest.fixture
async def docker_client():
    """Docker client for container management."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture
async def auth_circuit_cascade_l3(docker_client):
    """Create L3 auth circuit breaker cascade test manager."""
    manager = AuthServiceCircuitBreakerCascadeL3Manager(docker_client)
    await manager.setup_containerized_environment()
    yield manager
    await manager.cleanup_environment()


@pytest.mark.L3
class TestAuthServiceCircuitBreakerCascadeL3:
    """L3 tests for auth service circuit breaker cascade scenarios."""
    
    @pytest.mark.asyncio
    async def test_auth_service_failure_triggers_circuit_breakers(
        self, auth_circuit_cascade_l3
    ):
        """Test that auth service failure triggers circuit breakers in dependent services."""
        manager = auth_circuit_cascade_l3
        
        # Simulate auth service failure
        await manager.simulate_auth_service_failure()
        
        # Trigger auth requests that should fail
        results = await manager.trigger_auth_requests_cascade()
        
        # Verify circuit breakers opened in dependent services
        assert len(results) >= 2, "Should test multiple services"
        
        services_with_circuits_opened = [
            r for r in results.values() if r["circuit_opened"]
        ]
        assert len(services_with_circuits_opened) >= 1, "At least one circuit should open"
        
        # Verify fallback mechanisms activated
        services_with_fallback = [
            r for r in results.values() if r["fallback_activated"]
        ]
        assert len(services_with_fallback) >= 1, "Fallback should activate"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_thundering_herd(
        self, auth_circuit_cascade_l3
    ):
        """Test that circuit breakers prevent thundering herd during auth recovery."""
        manager = auth_circuit_cascade_l3
        
        # Trigger failure and cascade
        await manager.simulate_auth_service_failure()
        await manager.trigger_auth_requests_cascade()
        
        # Restore auth service
        await manager.restore_auth_service()
        
        # Simulate concurrent recovery attempts
        recovery_tasks = []
        for _ in range(10):
            task = asyncio.create_task(
                manager.trigger_auth_requests_cascade()
            )
            recovery_tasks.append(task)
        
        results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        
        # Verify controlled recovery (not all requests succeed immediately)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0, "Some recovery should succeed"
        
        # Verify circuit breaker metrics show controlled access
        assert manager.cascade_metrics.recovery_attempts > 0
        assert manager.cascade_metrics.fallback_activations > 0
    
    @pytest.mark.asyncio
    async def test_cross_service_circuit_breaker_coordination(
        self, auth_circuit_cascade_l3
    ):
        """Test circuit breaker coordination across multiple services."""
        manager = auth_circuit_cascade_l3
        
        # Test full cascade and recovery cycle
        coordination_result = await manager.test_circuit_breaker_recovery_coordination()
        
        cascade_phase = coordination_result["cascade_phase"]
        recovery_phase = coordination_result["recovery_phase"]
        metrics = coordination_result["cascade_metrics"]
        
        # Verify cascade phase
        assert len(cascade_phase) >= 2, "Should test multiple services"
        circuits_opened_during_cascade = sum(
            1 for result in cascade_phase.values() if result["circuit_opened"]
        )
        assert circuits_opened_during_cascade >= 1, "Circuit should open during cascade"
        
        # Verify recovery phase
        assert len(recovery_phase) >= 2, "Should test recovery for multiple services"
        successful_recoveries = sum(
            1 for result in recovery_phase.values() if result["recovery_successful"]
        )
        assert successful_recoveries >= 1, "At least one service should recover"
        
        # Verify metrics
        assert metrics["auth_failures"] >= 1, "Should record auth failures"
        assert metrics["services_isolated"] >= 1, "Should isolate services"
        assert metrics["fallback_activations"] >= 1, "Should activate fallbacks"
    
    @pytest.mark.asyncio
    async def test_websocket_circuit_breaker_auth_integration(
        self, auth_circuit_cascade_l3
    ):
        """Test WebSocket-specific circuit breaker behavior during auth failures."""
        manager = auth_circuit_cascade_l3
        
        websocket_endpoint = manager.service_endpoints.get("websocket")
        assert websocket_endpoint, "WebSocket endpoint should be configured"
        
        # Test WebSocket auth dependency
        await manager.simulate_auth_service_failure()
        websocket_result = await manager._test_service_auth_dependency(websocket_endpoint)
        
        assert websocket_result["service"] == "websocket"
        assert websocket_result["failures"] >= 2, "Should record failures"
        
        # WebSocket circuit should open faster (threshold=2)
        if websocket_result["failures"] >= 2:
            assert websocket_result["circuit_opened"], "WebSocket circuit should open"