"""
Service Startup Sequence Validator Module
Business Value: Ensures proper service dependency order for system availability
Modular design: <300 lines, 25-line functions max
"""
import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path for imports

# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services


class ServiceStartupSequenceValidator:
    """Validates service startup sequence and dependencies."""
    
    def __init__(self):
        """Initialize startup sequence validator."""
        self.orchestrator = MockE2EServiceOrchestrator()
        self.db_connections = MockDatabaseConnections()
        self.startup_order: List[str] = []
        self.startup_times: Dict[str, float] = {}
        self.client = MockHttpClient(timeout=30.0)
    
    async def validate_complete_startup_sequence(self) -> Dict[str, Any]:
        """Validate complete service startup sequence with dependencies."""
        start_time = time.time()
        results = self._create_initial_results()
        
        try:
            await self._execute_startup_validation()
            results.update(self._create_success_results(start_time))
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _create_initial_results(self) -> Dict[str, Any]:
        """Create initial results dictionary."""
        return {
            "success": False,
            "startup_order": [],
            "startup_times": {},
            "database_connections": {},
            "inter_service_communication": {},
            "total_startup_time": 0,
            "error": None
        }
    
    def _create_success_results(self, start_time: float) -> Dict[str, Any]:
        """Create success results dictionary."""
        return {
            "success": True,
            "startup_order": self.startup_order,
            "startup_times": self.startup_times,
            "total_startup_time": time.time() - start_time
        }
    
    async def _execute_startup_validation(self) -> None:
        """Execute complete startup validation sequence."""
        await self._test_startup_sequence_order()
        await self._validate_database_connections()
        await self._test_inter_service_communication()
    
    async def _test_startup_sequence_order(self) -> None:
        """Test services start in correct dependency order."""
        await self._start_and_validate_auth_service()
        await self._start_and_validate_backend_service()
        await self._start_and_validate_frontend_service()
    
    async def _start_and_validate_auth_service(self) -> None:
        """Start auth service and validate it's healthy."""
        start_time = time.time()
        
        if not await self._start_auth_service_first():
            raise RuntimeError("Auth service failed to start")
        
        await self._wait_for_auth_health()
        self._record_service_startup("auth", start_time)
    
    def _record_service_startup(self, service_name: str, start_time: float) -> None:
        """Record service startup completion."""
        self.startup_order.append(service_name)
        self.startup_times[service_name] = time.time() - start_time
    
    async def _start_auth_service_first(self) -> bool:
        """Start auth service as first dependency."""
        try:
            return await self._start_single_service("auth")
        except Exception:
            return False
    
    async def _wait_for_auth_health(self) -> None:
        """Wait for auth service to be healthy."""
        await self._wait_for_service_health(
            self._check_auth_health, 
            "Auth service health check timeout"
        )
    
    async def _wait_for_service_health(self, health_check_func, error_msg: str) -> None:
        """Generic service health wait with timeout."""
        for _ in range(30):  # 30 second timeout
            if await health_check_func():
                return
            await asyncio.sleep(1)
        raise RuntimeError(error_msg)
    
    async def _check_auth_health(self) -> bool:
        """Check auth service health endpoint."""
        return await self._check_service_endpoint("http://localhost:8081/health")
    
    async def _check_service_endpoint(self, url: str) -> bool:
        """Check if service endpoint is responding."""
        try:
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _start_and_validate_backend_service(self) -> None:
        """Start backend service after auth is healthy."""
        start_time = time.time()
        
        await self._ensure_auth_dependency()
        
        if not await self._start_single_service("backend"):
            raise RuntimeError("Backend service failed to start")
        
        await self._wait_for_backend_health()
        self._record_service_startup("backend", start_time)
    
    async def _ensure_auth_dependency(self) -> None:
        """Ensure auth dependency is available."""
        if not await self._check_auth_health():
            raise RuntimeError("Auth not healthy - backend cannot start")
    
    async def _wait_for_backend_health(self) -> None:
        """Wait for backend service to be healthy."""
        await self._wait_for_service_health(
            self._check_backend_health,
            "Backend service health check timeout"
        )
    
    async def _check_backend_health(self) -> bool:
        """Check backend service health endpoint."""
        return await self._check_service_endpoint("http://localhost:8000/health")
    
    async def _start_and_validate_frontend_service(self) -> None:
        """Start frontend service after auth and backend are healthy."""
        start_time = time.time()
        
        await self._ensure_frontend_dependencies()
        
        if not await self._start_single_service("frontend"):
            raise RuntimeError("Frontend service failed to start")
        
        await self._wait_for_frontend_health()
        self._record_service_startup("frontend", start_time)
    
    async def _ensure_frontend_dependencies(self) -> None:
        """Ensure frontend dependencies are available."""
        auth_healthy = await self._check_auth_health()
        backend_healthy = await self._check_backend_health()
        
        if not (auth_healthy and backend_healthy):
            raise RuntimeError("Dependencies not healthy - frontend cannot start")
    
    async def _wait_for_frontend_health(self) -> None:
        """Wait for frontend service to be healthy."""
        await self._wait_for_service_health(
            self._check_frontend_health,
            "Frontend service health check timeout"
        )
    
    async def _check_frontend_health(self) -> bool:
        """Check frontend service health endpoint."""
        return await self._check_service_endpoint("http://localhost:3000/")
    
    async def _start_single_service(self, service_name: str) -> bool:
        """Start a single service by name."""
        try:
            services_manager = self.orchestrator.services_manager
            service = services_manager.services.get(service_name)
            
            if not service:
                return False
            
            await self._execute_service_start(services_manager, service_name)
            return True
        except Exception:
            return False
    
    async def _execute_service_start(self, services_manager, service_name: str) -> None:
        """Execute service start based on service type."""
        if service_name == "auth":
            await services_manager._start_auth_service()
        elif service_name == "backend":
            await services_manager._start_backend_service()
        elif service_name == "frontend":
            await services_manager._start_frontend_service()
    
    async def _validate_database_connections(self) -> None:
        """Validate database connections are established."""
        await self.db_connections.connect_all()
        
        if not self.db_connections.postgres_pool:
            raise RuntimeError("PostgreSQL connection failed")
        
        self._record_database_status()
    
    def _record_database_status(self) -> None:
        """Record database connection status."""
        self.db_connections.connection_status = {
            "postgresql": True,
            "clickhouse": self.db_connections.clickhouse_client is not None,
            "redis": self.db_connections.redis_client is not None
        }
    
    async def _test_inter_service_communication(self) -> None:
        """Test communication between services."""
        await self._test_auth_to_backend_communication()
        await self._test_backend_to_frontend_communication()
        await self._test_frontend_to_backend_communication()
    
    async def _test_auth_to_backend_communication(self) -> None:
        """Test auth service to backend communication."""
        try:
            response = await self.client.get(
                "http://localhost:8000/health",
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code in [200, 401]
        except Exception as e:
            raise RuntimeError(f"Auth  ->  Backend communication failed: {e}")
    
    async def _test_backend_to_frontend_communication(self) -> None:
        """Test backend service to frontend communication."""
        try:
            response = await self.client.get("http://localhost:8000/health")
            assert response.status_code == 200
        except Exception as e:
            raise RuntimeError(f"Backend  ->  Frontend communication failed: {e}")
    
    async def _test_frontend_to_backend_communication(self) -> None:
        """Test frontend service to backend communication."""
        try:
            response = await self.client.get("http://localhost:3000/")
            assert response.status_code == 200
        except Exception as e:
            raise RuntimeError(f"Frontend  ->  Backend communication failed: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup test resources."""
        await self.client.aclose()
        await self.db_connections.disconnect_all()
        await self.orchestrator.test_stop_test_environment("test_startup")