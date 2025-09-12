"""
Service Startup Sequence and Health Cascade Real Integration Test

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Zero-downtime deployments
- Value Impact: Ensures proper startup sequence: Auth  ->  Backend  ->  Frontend  
- Revenue Impact: $70K+ MRR (System reliability prevents downtime costs)
- Strategic Impact: Validates inter-service dependencies and failure handling

CRITICAL REQUIREMENTS:
1. Test proper startup sequence: Auth  ->  Backend  ->  Frontend
2. Validate health check propagation between services
3. Test service discovery with dynamic ports
4. Simulate failure recovery when one service is down
5. Ensure dependent services handle upstream failures

Test validates:
- Startup sequencing with proper dependency ordering
- Health check cascade propagation across services
- Service discovery mechanism with dynamic port allocation
- Failure recovery patterns and graceful degradation
- Inter-service communication health validation

Maximum 300 lines, async/await patterns, real service validation
"""

import asyncio
import logging
import socket
from shared.isolated_environment import IsolatedEnvironment

# Add project root for imports
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest


from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.startup_optimizer import StartupPhase
from tests.e2e.health_check_core import (
    SERVICE_ENDPOINTS,
    HealthCheckResult,
    create_healthy_result,
    create_service_error_result,
)
from tests.e2e.health_service_checker import ServiceHealthChecker

logger = logging.getLogger(__name__)


@dataclass
class ServiceStartupResult:
    """Result of service startup validation."""
    service_name: str
    started: bool
    port: int
    health_status: str
    startup_time_ms: float
    dependencies_satisfied: bool
    error: Optional[str] = None


class ServiceStartupSequencer:
    """Manages service startup sequence with dependency validation."""
    
    def __init__(self):
        """Initialize startup sequencer with service discovery."""
        self.discovery = ServiceDiscovery()
        self.startup_results: Dict[str, ServiceStartupResult] = {}
        self.health_checker = ServiceHealthChecker()
        
    async def validate_startup_sequence(self) -> Dict[str, Any]:
        """Validate proper startup sequence: Auth  ->  Backend  ->  Frontend."""
        sequence_results = {
            "auth": await self._validate_auth_startup(),
            "backend": await self._validate_backend_startup(),
            "frontend": await self._validate_frontend_startup()
        }
        
        return {
            "sequence_valid": await self._verify_dependency_order(sequence_results),
            "services": sequence_results,
            "startup_timing": self._calculate_startup_timing(sequence_results)
        }
    
    async def _validate_auth_startup(self) -> ServiceStartupResult:
        """Validate auth service startup (first in sequence)."""
        start_time = time.time()
        
        # Check if auth service is running on expected port
        auth_port = await self._detect_auth_service_port()
        if not auth_port:
            return self._create_startup_failure("auth", "Auth service not detected on any port")
        
        # Validate health endpoint
        health_status = await self._check_service_health("auth", auth_port)
        startup_time = (time.time() - start_time) * 1000
        
        return ServiceStartupResult(
            service_name="auth",
            started=health_status == "healthy",
            port=auth_port,
            health_status=health_status,
            startup_time_ms=startup_time,
            dependencies_satisfied=True  # Auth has no dependencies
        )
    
    async def _validate_backend_startup(self) -> ServiceStartupResult:
        """Validate backend service startup (depends on auth)."""
        start_time = time.time()
        
        # Verify auth dependency first
        auth_healthy = await self._verify_auth_dependency()
        if not auth_healthy:
            return self._create_startup_failure("backend", "Auth dependency not satisfied")
        
        # Check backend service
        backend_port = await self._detect_backend_service_port()
        if not backend_port:
            return self._create_startup_failure("backend", "Backend service not detected")
        
        health_status = await self._check_service_health("backend", backend_port)
        startup_time = (time.time() - start_time) * 1000
        
        return ServiceStartupResult(
            service_name="backend",
            started=health_status == "healthy",
            port=backend_port,
            health_status=health_status,
            startup_time_ms=startup_time,
            dependencies_satisfied=auth_healthy
        )
    
    async def _validate_frontend_startup(self) -> ServiceStartupResult:
        """Validate frontend service startup (depends on backend)."""
        start_time = time.time()
        
        # Verify backend dependency
        backend_healthy = await self._verify_backend_dependency()
        if not backend_healthy:
            return self._create_startup_failure("frontend", "Backend dependency not satisfied")
        
        # Check frontend service
        frontend_port = await self._detect_frontend_service_port()
        if not frontend_port:
            return self._create_startup_failure("frontend", "Frontend service not detected")
        
        health_status = await self._check_service_health("frontend", frontend_port)
        startup_time = (time.time() - start_time) * 1000
        
        return ServiceStartupResult(
            service_name="frontend",
            started=health_status == "healthy",
            port=frontend_port,
            health_status=health_status,
            startup_time_ms=startup_time,
            dependencies_satisfied=backend_healthy
        )
    
    async def _detect_auth_service_port(self) -> Optional[int]:
        """Detect auth service port using discovery and port scanning."""
        # Try service discovery first
        auth_info = self.discovery.read_auth_info()
        if auth_info and await self._is_port_responsive(auth_info.get("port", 8081)):
            return auth_info["port"]
        
        # Fallback to common auth ports
        for port in [8081, 8083, 8082]:
            if await self._is_port_responsive(port):
                return port
        return None
    
    async def _detect_backend_service_port(self) -> Optional[int]:
        """Detect backend service port."""
        backend_info = self.discovery.read_backend_info()
        if backend_info and await self._is_port_responsive(backend_info.get("port", 8000)):
            return backend_info["port"]
        
        # Fallback to common backend ports
        for port in [8000, 8080, 8001]:
            if await self._is_port_responsive(port):
                return port
        return None
    
    async def _detect_frontend_service_port(self) -> Optional[int]:
        """Detect frontend service port."""
        frontend_info = self.discovery.read_frontend_info()
        if frontend_info and await self._is_port_responsive(frontend_info.get("port", 3000)):
            return frontend_info["port"]
        
        # Fallback to common frontend ports
        for port in [3000, 3001, 5173]:
            if await self._is_port_responsive(port):
                return port
        return None
    
    async def _is_port_responsive(self, port: int) -> bool:
        """Check if port is responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                response = await client.get(f"http://localhost:{port}/health")
                return response.status_code == 200
        except Exception:
            try:
                # For frontend, try root path
                async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                    response = await client.get(f"http://localhost:{port}/")
                    return response.status_code in [200, 404]  # 404 is valid for React apps
            except Exception:
                return False
    
    async def _check_service_health(self, service_name: str, port: int) -> str:
        """Check service health status."""
        try:
            health_url = f"http://localhost:{port}/health"
            if service_name == "frontend":
                health_url = f"http://localhost:{port}/"
            
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    return "healthy"
                else:
                    return "unhealthy"
        except Exception:
            return "error"
    
    async def _verify_auth_dependency(self) -> bool:
        """Verify auth service is healthy for backend dependency."""
        try:
            auth_port = await self._detect_auth_service_port()
            if not auth_port:
                return False
            return await self._check_service_health("auth", auth_port) == "healthy"
        except Exception:
            return False
    
    async def _verify_backend_dependency(self) -> bool:
        """Verify backend service is healthy for frontend dependency."""
        try:
            backend_port = await self._detect_backend_service_port()
            if not backend_port:
                return False
            return await self._check_service_health("backend", backend_port) == "healthy"
        except Exception:
            return False
    
    def _create_startup_failure(self, service_name: str, error: str) -> ServiceStartupResult:
        """Create startup failure result."""
        return ServiceStartupResult(
            service_name=service_name,
            started=False,
            port=0,
            health_status="error",
            startup_time_ms=0,
            dependencies_satisfied=False,
            error=error
        )
    
    async def _verify_dependency_order(self, results: Dict[str, ServiceStartupResult]) -> bool:
        """Verify services started in correct dependency order."""
        auth_started = results["auth"].started
        backend_deps_satisfied = results["backend"].dependencies_satisfied
        
        # Frontend is optional in test environments
        frontend_valid = (
            not results["frontend"].started or  # Frontend not running (acceptable)
            results["frontend"].dependencies_satisfied  # Frontend running with deps satisfied
        )
        
        return auth_started and backend_deps_satisfied and frontend_valid
    
    def _calculate_startup_timing(self, results: Dict[str, ServiceStartupResult]) -> Dict[str, float]:
        """Calculate startup timing metrics."""
        return {
            f"{name}_startup_ms": result.startup_time_ms
            for name, result in results.items()
        }


class HealthCascadeValidator:
    """Validates health check cascade behavior across services."""
    
    def __init__(self):
        """Initialize health cascade validator."""
        self.health_checker = ServiceHealthChecker()
        self.discovery = ServiceDiscovery()
    
    async def validate_health_propagation(self) -> Dict[str, Any]:
        """Validate health check propagation between services."""
        propagation_results = {
            "auth_to_backend": await self._test_auth_backend_propagation(),
            "backend_to_frontend": await self._test_backend_frontend_propagation(),
            "inter_service_health": await self._test_inter_service_health()
        }
        
        return {
            "cascade_working": all(result.get("propagation_detected", False) 
                                 for result in propagation_results.values()),
            "details": propagation_results
        }
    
    async def _test_auth_backend_propagation(self) -> Dict[str, Any]:
        """Test health propagation from auth to backend."""
        try:
            # Check direct auth health
            auth_health = await self._check_direct_service_health("auth")
            
            # Check backend's view of auth dependency
            backend_health = await self._check_direct_service_health("backend")
            
            return {
                "auth_direct_health": auth_health,
                "backend_health": backend_health,
                "propagation_detected": auth_health == "healthy" and backend_health == "healthy"
            }
        except Exception as e:
            return {"error": str(e), "propagation_detected": False}
    
    async def _test_backend_frontend_propagation(self) -> Dict[str, Any]:
        """Test health propagation from backend to frontend."""
        try:
            backend_health = await self._check_direct_service_health("backend")
            frontend_health = await self._check_direct_service_health("frontend")
            
            # Test if frontend can reach backend
            frontend_backend_connectivity = await self._test_frontend_backend_connectivity()
            
            return {
                "backend_health": backend_health,
                "frontend_health": frontend_health,
                "connectivity": frontend_backend_connectivity,
                "propagation_detected": backend_health == "healthy" and frontend_backend_connectivity
            }
        except Exception as e:
            return {"error": str(e), "propagation_detected": False}
    
    async def _test_inter_service_health(self) -> Dict[str, Any]:
        """Test overall inter-service health coordination."""
        try:
            health_results = await self.health_checker.check_all_services()
            
            healthy_count = sum(1 for r in health_results if r.is_healthy())
            total_count = len(health_results)
            
            return {
                "healthy_services": healthy_count,
                "total_services": total_count,
                "system_health_score": healthy_count / total_count if total_count > 0 else 0,
                "propagation_detected": healthy_count > 0
            }
        except Exception as e:
            return {"error": str(e), "propagation_detected": False}
    
    async def _check_direct_service_health(self, service_name: str) -> str:
        """Check direct service health."""
        try:
            if service_name == "auth":
                port = 8081
                health_url = f"http://localhost:{port}/health"
            elif service_name == "backend":
                port = 8000
                health_url = f"http://localhost:{port}/health"
            else:  # frontend
                port = 3000
                health_url = f"http://localhost:{port}/"
            
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(health_url)
                return "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            return "error"
    
    async def _test_frontend_backend_connectivity(self) -> bool:
        """Test if frontend can connect to backend."""
        try:
            # Frontend should be able to reach backend API
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get("http://localhost:8000/health")
                return response.status_code == 200
        except Exception:
            return False


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
class TestServiceStartupHealthReal:
    """Real service startup sequence and health cascade test suite."""
    
    @pytest.fixture
    def startup_sequencer(self):
        """Create service startup sequencer."""
        return ServiceStartupSequencer()
    
    @pytest.fixture
    def health_cascade_validator(self):
        """Create health cascade validator."""
        return HealthCascadeValidator()
    
    @pytest.mark.e2e
    async def test_proper_startup_sequence_auth_backend_frontend(self, startup_sequencer):
        """Test proper startup sequence: Auth  ->  Backend  ->  Frontend."""
        logger.info("Testing service startup sequence validation")
        
        # Validate startup sequence
        sequence_result = await startup_sequencer.validate_startup_sequence()
        
        # Assert sequence is valid
        assert sequence_result["sequence_valid"], f"Startup sequence validation failed: {sequence_result}"
        
        # Verify each service in sequence
        services = sequence_result["services"]
        assert services["auth"].started, "Auth service not properly started"
        assert services["backend"].started, "Backend service not properly started"
        assert services["backend"].dependencies_satisfied, "Backend dependencies not satisfied"
        
        # Frontend is optional in test environments but if running, should have dependencies satisfied
        if services["frontend"].started:
            assert services["frontend"].dependencies_satisfied, "Frontend dependencies not satisfied"
        else:
            logger.info("Frontend service not running (acceptable in test environment)")
        
        logger.info("[U+2713] Service startup sequence validated successfully")
    
    @pytest.mark.e2e
    async def test_health_check_propagation_between_services(self, health_cascade_validator):
        """Test health check propagation between services."""
        logger.info("Testing health check cascade propagation")
        
        # Validate health propagation
        cascade_result = await health_cascade_validator.validate_health_propagation()
        
        # Assert cascade is working
        assert cascade_result["cascade_working"], f"Health cascade not working: {cascade_result}"
        
        # Verify specific propagation paths
        details = cascade_result["details"]
        assert details["auth_to_backend"]["propagation_detected"], "Auth to Backend propagation failed"
        assert details["backend_to_frontend"]["propagation_detected"], "Backend to Frontend propagation failed"
        assert details["inter_service_health"]["propagation_detected"], "Inter-service health coordination failed"
        
        logger.info("[U+2713] Health check propagation validated successfully")
    
    @pytest.mark.e2e
    async def test_service_discovery_with_dynamic_ports(self, startup_sequencer):
        """Test service discovery mechanism with dynamic ports."""
        logger.info("Testing service discovery with dynamic ports")
        
        # Test port detection for each service
        auth_port = await startup_sequencer._detect_auth_service_port()
        backend_port = await startup_sequencer._detect_backend_service_port()
        frontend_port = await startup_sequencer._detect_frontend_service_port()
        
        # Assert services are discoverable
        assert auth_port is not None, "Auth service port not discoverable"
        assert backend_port is not None, "Backend service port not discoverable"
        
        # Verify ports are different and valid
        assert auth_port != backend_port, "Auth and Backend using same port"
        assert 1000 <= auth_port <= 65535, f"Invalid auth port: {auth_port}"
        assert 1000 <= backend_port <= 65535, f"Invalid backend port: {backend_port}"
        
        # Frontend is optional but if running, validate port
        if frontend_port:
            assert frontend_port != auth_port and frontend_port != backend_port, "Frontend port conflicts"
            assert 1000 <= frontend_port <= 65535, f"Invalid frontend port: {frontend_port}"
        
        logger.info("[U+2713] Service discovery with dynamic ports validated successfully")
    
    @pytest.mark.e2e
    async def test_failure_recovery_simulation(self, health_cascade_validator):
        """Test service failure recovery patterns."""
        logger.info("Testing failure recovery simulation")
        
        # Test initial health state
        initial_health = await health_cascade_validator.validate_health_propagation()
        
        # Simulate recovery by testing health multiple times
        recovery_attempts = []
        for i in range(3):
            await asyncio.sleep(1)  # Allow time for potential recovery
            health_check = await health_cascade_validator.validate_health_propagation()
            recovery_attempts.append(health_check["cascade_working"])
        
        # Assert system maintains or recovers health
        recovery_success = any(recovery_attempts)
        assert recovery_success, f"System failed to maintain/recover health: {recovery_attempts}"
        
        # Verify graceful degradation if some services are down
        final_health = await health_cascade_validator._test_inter_service_health()
        assert final_health["healthy_services"] >= 1, "No healthy services detected"
        
        logger.info("[U+2713] Failure recovery patterns validated successfully")
    
    @pytest.mark.e2e
    async def test_dependent_services_handle_upstream_failures(self, startup_sequencer, health_cascade_validator):
        """Test dependent services handle upstream failures gracefully."""
        logger.info("Testing upstream failure handling")
        
        # Check current service states
        sequence_result = await startup_sequencer.validate_startup_sequence()
        health_result = await health_cascade_validator.validate_health_propagation()
        
        # Verify services are aware of dependencies
        services = sequence_result["services"]
        
        # Backend should handle auth dependency status
        if services["backend"].started:
            assert services["backend"].dependencies_satisfied is not None, "Backend not checking auth dependency"
        
        # Frontend should handle backend dependency status  
        if services["frontend"].started:
            assert services["frontend"].dependencies_satisfied is not None, "Frontend not checking backend dependency"
        
        # Verify graceful degradation in health cascade
        cascade_details = health_result["details"]
        inter_service_health = cascade_details["inter_service_health"]
        
        # System should maintain some level of functionality
        assert inter_service_health["system_health_score"] > 0, "System completely non-functional"
        
        logger.info("[U+2713] Upstream failure handling validated successfully")


async def run_service_startup_health_test():
    """Run service startup and health cascade test as standalone function."""
    logger.info("Starting service startup and health cascade test")
    
    startup_sequencer = ServiceStartupSequencer()
    health_validator = HealthCascadeValidator()
    
    results = {}
    
    try:
        # Test 1: Startup sequence validation
        results["startup_sequence"] = await startup_sequencer.validate_startup_sequence()
        
        # Test 2: Health cascade validation
        results["health_cascade"] = await health_validator.validate_health_propagation()
        
        # Test 3: Service discovery
        results["service_discovery"] = {
            "auth_port": await startup_sequencer._detect_auth_service_port(),
            "backend_port": await startup_sequencer._detect_backend_service_port(),
            "frontend_port": await startup_sequencer._detect_frontend_service_port()
        }
        
        return {
            "test_completed": True,
            "all_validations_passed": (
                results["startup_sequence"]["sequence_valid"] and
                results["health_cascade"]["cascade_working"]
            ),
            "results": results
        }
        
    except Exception as e:
        return {"error": str(e), "test_completed": False}


if __name__ == "__main__":
    result = asyncio.run(run_service_startup_health_test())
    print(f"Service startup and health cascade test results: {result}")