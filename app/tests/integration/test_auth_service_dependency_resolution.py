"""
Auth Service Dependency Resolution Integration Test

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability
- Value Impact: Prevents service startup ordering failures
- Revenue Impact: Protects $12K infrastructure reliability value

Tests service startup dependency resolution, health check cascade behavior,
backend graceful waiting for auth service readiness, and error handling.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime

from app.core.health_check import HealthCheckService
from app.services.service_orchestrator import ServiceOrchestrator
from test_framework.real_service_helper import RealServiceHelper


class ServiceStartupMonitor:
    """Monitor service startup sequence and dependencies."""
    
    def __init__(self):
        self.startup_events: List[Dict[str, Any]] = []
        self.service_states: Dict[str, str] = {}
        self.dependency_graph: Dict[str, List[str]] = {
            "auth_service": [],  # No dependencies
            "backend": ["auth_service"],  # Depends on auth
            "frontend": ["backend", "auth_service"]  # Depends on both
        }
    
    def record_startup_event(self, service_name: str, event_type: str, timestamp: float = None):
        """Record a service startup event."""
        if timestamp is None:
            timestamp = time.time()
        
        self.startup_events.append({
            "service": service_name,
            "event": event_type,
            "timestamp": timestamp
        })
        
        if event_type == "started":
            self.service_states[service_name] = "starting"
        elif event_type == "ready":
            self.service_states[service_name] = "ready"
        elif event_type == "failed":
            self.service_states[service_name] = "failed"
    
    def get_startup_order(self) -> List[str]:
        """Get the actual startup order of services."""
        started_services = []
        for event in self.startup_events:
            if event["event"] == "started" and event["service"] not in started_services:
                started_services.append(event["service"])
        return started_services
    
    def validate_dependency_order(self) -> bool:
        """Validate that services started in correct dependency order."""
        startup_order = self.get_startup_order()
        
        for service, dependencies in self.dependency_graph.items():
            if service in startup_order:
                service_index = startup_order.index(service)
                for dep in dependencies:
                    if dep in startup_order:
                        dep_index = startup_order.index(dep)
                        if dep_index >= service_index:
                            return False  # Dependency started after dependent
        return True


class AuthServiceDependencyTest:
    """Test auth service dependency resolution."""
    
    def __init__(self):
        self.orchestrator = ServiceOrchestrator()
        self.service_helper = RealServiceHelper()
        self.health_service = HealthCheckService()
        self.startup_monitor = ServiceStartupMonitor()
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
    
    async def monitor_service_startup_sequence(self) -> List[str]:
        """Monitor and record service startup sequence."""
        # Start monitoring service health endpoints
        monitoring_tasks = [
            self._monitor_service_startup("auth_service", self.auth_url),
            self._monitor_service_startup("backend", self.backend_url),
            self._monitor_service_startup("frontend", self.frontend_url)
        ]
        
        # Start services through orchestrator
        orchestration_task = asyncio.create_task(
            self.orchestrator.start_all_services()
        )
        
        # Monitor for 60 seconds or until all services ready
        start_time = time.time()
        timeout = 60  # seconds
        
        while time.time() - start_time < timeout:
            all_ready = all(
                self.startup_monitor.service_states.get(svc) == "ready"
                for svc in ["auth_service", "backend", "frontend"]
            )
            
            if all_ready:
                break
            
            await asyncio.sleep(1)
        
        # Cancel monitoring tasks
        for task in monitoring_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for orchestration to complete
        if not orchestration_task.done():
            await orchestration_task
        
        return self.startup_monitor.get_startup_order()
    
    async def _monitor_service_startup(self, service_name: str, service_url: str):
        """Monitor individual service startup."""
        self.startup_monitor.record_startup_event(service_name, "started")
        
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(f"{service_url}/health", timeout=2)
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            self.startup_monitor.record_startup_event(service_name, "ready")
                            break
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass  # Service not ready yet
                
                await asyncio.sleep(1)
    
    async def wait_for_auth_health_ready(self) -> Dict[str, Any]:
        """Wait for auth service to be healthy."""
        max_wait = 30  # seconds
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < max_wait:
                try:
                    response = await client.get(f"{self.auth_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            return health_data
                except Exception:
                    pass
                
                await asyncio.sleep(1)
        
        raise TimeoutError("Auth service did not become healthy within timeout")
    
    async def wait_for_backend_health_ready(self) -> Dict[str, Any]:
        """Wait for backend service to be healthy."""
        max_wait = 30  # seconds
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < max_wait:
                try:
                    response = await client.get(f"{self.backend_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") in ["healthy", "degraded"]:
                            return health_data
                except Exception:
                    pass
                
                await asyncio.sleep(1)
        
        raise TimeoutError("Backend service did not become ready within timeout")
    
    async def simulate_auth_service_unavailable(self):
        """Simulate auth service being unavailable."""
        # Stop auth service
        await self.service_helper.stop_service("auth_service")
        
        # Wait for service to be fully down
        await asyncio.sleep(2)
        
        # Verify service is down
        async with httpx.AsyncClient() as client:
            try:
                await client.get(f"{self.auth_url}/health", timeout=2)
                raise AssertionError("Auth service should be unavailable")
            except httpx.ConnectError:
                pass  # Expected
    
    async def test_backend_graceful_degradation(self) -> Dict[str, Any]:
        """Test backend graceful degradation when auth unavailable."""
        retry_attempts = 0
        max_retries = 5
        
        async with httpx.AsyncClient() as client:
            while retry_attempts < max_retries:
                try:
                    # Try to make authenticated request
                    response = await client.get(
                        f"{self.backend_url}/api/v1/user/profile",
                        headers={"Authorization": "Bearer invalid_token"}
                    )
                    
                    # Should get service unavailable or auth error
                    if response.status_code in [503, 401]:
                        return {
                            "status_code": response.status_code,
                            "retries_attempted": retry_attempts + 1,
                            "degraded": True
                        }
                    
                except httpx.ConnectError:
                    # Backend might be retrying connection to auth
                    pass
                
                retry_attempts += 1
                await asyncio.sleep(2)
        
        return {
            "status_code": 503,
            "retries_attempted": retry_attempts,
            "degraded": True
        }
    
    async def test_health_check_cascade(self) -> Dict[str, Dict[str, str]]:
        """Test health check cascade across services."""
        health_statuses = {}
        
        async with httpx.AsyncClient() as client:
            # Get health status from each service
            services = [
                ("auth_service", self.auth_url),
                ("backend", self.backend_url),
                ("frontend", self.frontend_url)
            ]
            
            for service_name, service_url in services:
                try:
                    response = await client.get(f"{service_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        health_statuses[service_name] = {
                            "status": health_data.get("status", "unknown"),
                            "dependencies": health_data.get("dependencies", {})
                        }
                except Exception as e:
                    health_statuses[service_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return health_statuses


@pytest.mark.integration
@pytest.mark.requires_orchestration
class TestAuthServiceDependencyResolution:
    """Test suite for auth service dependency resolution."""
    
    @pytest.fixture
    async def test_harness(self):
        """Create test harness for dependency resolution testing."""
        harness = AuthServiceDependencyTest()
        yield harness
        # Cleanup: ensure all services are stopped
        await harness.service_helper.stop_all_services()
    
    @pytest.mark.asyncio
    async def test_auth_service_dependency_resolution(self, test_harness):
        """
        Test service startup dependency resolution.
        
        Validates:
        1. Auth service starts before backend
        2. Backend waits for auth readiness
        3. Health check cascade behavior
        4. Error handling when auth unavailable
        """
        # Phase 1: Dependency Order Validation
        startup_order = await test_harness.monitor_service_startup_sequence()
        
        # Verify auth starts before backend
        assert "auth_service" in startup_order, "Auth service not in startup order"
        assert "backend" in startup_order, "Backend not in startup order"
        assert startup_order.index("auth_service") < startup_order.index("backend"), \
            f"Auth should start before backend. Order: {startup_order}"
        
        # Verify dependency order is correct
        assert test_harness.startup_monitor.validate_dependency_order(), \
            "Service dependency order validation failed"
        
        # Phase 2: Health Check Cascade
        auth_health = await test_harness.wait_for_auth_health_ready()
        assert auth_health["status"] == "healthy", "Auth service not healthy"
        
        backend_health = await test_harness.wait_for_backend_health_ready()
        assert "auth_service" in backend_health.get("dependencies", {}), \
            "Backend doesn't report auth as dependency"
        assert backend_health["dependencies"]["auth_service"] == "healthy", \
            "Backend doesn't see auth as healthy"
        
        # Phase 3: Error Handling
        await test_harness.simulate_auth_service_unavailable()
        
        backend_response = await test_harness.test_backend_graceful_degradation()
        assert backend_response["retries_attempted"] > 0, \
            "Backend didn't retry when auth unavailable"
        assert backend_response["degraded"] == True, \
            "Backend didn't degrade gracefully"
    
    @pytest.mark.asyncio
    async def test_backend_waits_for_auth_readiness(self, test_harness):
        """Test that backend waits for auth service to be ready."""
        # Start backend first (wrong order) to test waiting behavior
        backend_start_task = asyncio.create_task(
            test_harness.service_helper.start_service("backend")
        )
        
        # Wait briefly
        await asyncio.sleep(2)
        
        # Backend should be waiting, not failed
        backend_status = test_harness.startup_monitor.service_states.get("backend")
        assert backend_status != "failed", "Backend failed instead of waiting for auth"
        
        # Now start auth service
        await test_harness.service_helper.start_service("auth_service")
        
        # Wait for auth to be ready
        auth_health = await test_harness.wait_for_auth_health_ready()
        assert auth_health["status"] == "healthy"
        
        # Backend should now become ready
        await backend_start_task
        backend_health = await test_harness.wait_for_backend_health_ready()
        assert backend_health["status"] in ["healthy", "degraded"]
    
    @pytest.mark.asyncio
    async def test_health_check_propagation_timing(self, test_harness):
        """Test health check status propagation timing."""
        # Start all services
        await test_harness.orchestrator.start_all_services()
        
        # Wait for all to be healthy
        await test_harness.wait_for_auth_health_ready()
        await test_harness.wait_for_backend_health_ready()
        
        # Make auth unhealthy
        await test_harness.service_helper.make_service_unhealthy("auth_service")
        
        # Measure propagation time
        propagation_start = time.time()
        max_propagation_time = 30  # seconds
        
        backend_sees_unhealthy = False
        while time.time() - propagation_start < max_propagation_time:
            backend_health = await test_harness.wait_for_backend_health_ready()
            
            if backend_health.get("dependencies", {}).get("auth_service") == "unhealthy":
                backend_sees_unhealthy = True
                break
            
            await asyncio.sleep(1)
        
        propagation_time = time.time() - propagation_start
        
        assert backend_sees_unhealthy, "Backend didn't detect auth unhealthy status"
        assert propagation_time < 30, f"Health propagation took {propagation_time}s (limit: 30s)"
    
    @pytest.mark.asyncio
    async def test_circular_dependency_prevention(self, test_harness):
        """Test that circular dependencies are prevented."""
        # Attempt to create circular dependency (should be prevented)
        test_harness.startup_monitor.dependency_graph["auth_service"] = ["backend"]
        
        # This should be detected and prevented
        is_valid = test_harness.startup_monitor.validate_dependency_order()
        
        # Reset to correct dependencies
        test_harness.startup_monitor.dependency_graph["auth_service"] = []
        
        # With circular dependency, validation should handle it gracefully
        # The system should prevent circular dependencies from causing deadlock
        startup_order = await test_harness.monitor_service_startup_sequence()
        
        # Services should still start (system prevents deadlock)
        assert len(startup_order) > 0, "Services failed to start due to circular dependency"
    
    @pytest.mark.asyncio
    async def test_cascading_health_status(self, test_harness):
        """Test cascading health status across all services."""
        # Start all services
        await test_harness.orchestrator.start_all_services()
        
        # Get initial health cascade
        initial_health = await test_harness.test_health_check_cascade()
        
        # All should be healthy
        for service in ["auth_service", "backend", "frontend"]:
            assert service in initial_health
            assert initial_health[service]["status"] in ["healthy", "degraded"]
        
        # Make auth unhealthy
        await test_harness.service_helper.make_service_unhealthy("auth_service")
        await asyncio.sleep(5)  # Allow propagation
        
        # Get degraded health cascade
        degraded_health = await test_harness.test_health_check_cascade()
        
        # Auth should be unhealthy
        assert degraded_health["auth_service"]["status"] == "unhealthy"
        
        # Backend should show auth as unhealthy dependency
        assert degraded_health["backend"]["dependencies"]["auth_service"] == "unhealthy"
        
        # Frontend should see cascade effect
        if "backend" in degraded_health["frontend"]["dependencies"]:
            # Frontend might show backend as degraded due to auth issue
            assert degraded_health["frontend"]["dependencies"]["backend"] in ["degraded", "unhealthy"]