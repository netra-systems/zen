"""
Integration tests for service coordination system.

Tests all the coordination components together to ensure they resolve
the issues identified in test_critical_cold_start_initialization.py.
"""

import asyncio
import logging
import pytest
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from dev_launcher.dependency_manager import (
    DependencyManager, 
    ServiceDependency, 
    DependencyType,
    setup_default_dependency_manager
)
from dev_launcher.service_coordinator import (
    ServiceCoordinator, 
    CoordinationConfig,
    CoordinationState
)
from dev_launcher.readiness_checker import (
    ReadinessManager,
    ReadinessState,
    BackendReadinessChecker,
    FrontendReadinessChecker,
    AuthServiceReadinessChecker
)
from dev_launcher.port_allocator import PortAllocator, AllocationResult
from dev_launcher.service_registry import (
    ServiceRegistry,
    ServiceEndpoint,
    ServiceStatus,
    DiscoveryQuery
)

logger = logging.getLogger(__name__)


class TestServiceCoordinationIntegration:
    """Integration tests for the complete service coordination system."""
    
    @pytest.fixture
    def temp_registry_dir(self, tmp_path):
        """Create temporary directory for service registry."""
        registry_dir = tmp_path / "service_registry"
        registry_dir.mkdir()
        return registry_dir
    
    @pytest.fixture
    async def port_allocator(self):
        """Create and start port allocator."""
        allocator = PortAllocator(default_reservation_timeout=30.0)
        await allocator.start()
        yield allocator
        await allocator.stop()
    
    @pytest.fixture
    async def service_registry(self, temp_registry_dir):
        """Create and start service registry."""
        registry = ServiceRegistry(registry_dir=temp_registry_dir)
        await registry.start()
        yield registry
        await registry.stop()
    
    @pytest.fixture
    def readiness_manager(self):
        """Create readiness manager."""
        return ReadinessManager()
    
    @pytest.fixture
    def dependency_manager(self):
        """Create dependency manager with default dependencies."""
        return setup_default_dependency_manager()
    
    @pytest.fixture
    def service_coordinator(self):
        """Create service coordinator."""
        config = CoordinationConfig(
            max_parallel_starts=2,
            dependency_timeout=30,
            readiness_timeout=60,
            startup_retry_count=1,
            enable_graceful_degradation=True,
            required_services={"database", "backend"},
            optional_services={"redis", "auth", "frontend"}
        )
        return ServiceCoordinator(config)
    
    @pytest.mark.asyncio
    async def test_dependency_resolution_prevents_early_startup(self, dependency_manager):
        """Test that dependency resolution prevents services from starting before dependencies."""
        # This addresses test_06_services_starting_before_dependencies
        
        # Add services with dependencies
        dependency_manager.add_service("database", [])
        dependency_manager.add_service("auth", [
            ServiceDependency("auth", "database", DependencyType.REQUIRED, timeout=10)
        ])
        dependency_manager.add_service("backend", [
            ServiceDependency("backend", "database", DependencyType.REQUIRED, timeout=10),
            ServiceDependency("backend", "auth", DependencyType.REQUIRED, timeout=15)
        ])
        
        # Get startup order
        startup_order = dependency_manager.get_startup_order()
        
        # Verify correct order
        assert startup_order.index("database") < startup_order.index("auth")
        assert startup_order.index("auth") < startup_order.index("backend")
        
        # Test dependency waiting
        await dependency_manager.mark_service_ready("database")
        
        # Auth can start after database is ready
        auth_dependencies_ready = await dependency_manager.wait_for_dependencies("auth")
        assert auth_dependencies_ready is True
        
        # Backend cannot start until auth is ready
        backend_dependencies_ready = await asyncio.wait_for(
            dependency_manager.wait_for_dependencies("backend"),
            timeout=2.0
        )
        assert backend_dependencies_ready is False  # Auth not ready yet
        
        # Mark auth ready, then backend can start
        await dependency_manager.mark_service_ready("auth")
        backend_dependencies_ready = await dependency_manager.wait_for_dependencies("backend")
        assert backend_dependencies_ready is True
    
    @pytest.mark.asyncio
    async def test_readiness_vs_health_separation(self, readiness_manager):
        """Test separation between readiness and health checks."""
        # This addresses test_07_health_check_false_positives_during_init
        
        # Register a service with readiness checker
        backend_checker = BackendReadinessChecker(port=8000)
        readiness_manager.register_checker("backend", backend_checker)
        
        # Initially, service should not be ready
        assert not readiness_manager.is_service_ready("backend")
        
        # Mark as initializing
        await readiness_manager.mark_service_initializing("backend")
        assert not readiness_manager.is_service_ready("backend")
        
        # Mark as starting
        await readiness_manager.mark_service_starting("backend")
        assert not readiness_manager.is_service_ready("backend")
        
        # Only after proper readiness check should it be ready
        with patch.object(backend_checker, 'check_ready', return_value=True):
            ready = await readiness_manager.check_service_ready("backend")
            assert ready is True
            assert readiness_manager.is_service_ready("backend")
    
    @pytest.mark.asyncio
    async def test_port_allocation_prevents_conflicts(self, port_allocator):
        """Test port allocation prevents binding conflicts."""
        # This addresses test_08_port_binding_race_conditions
        
        # Try to allocate same port to multiple services
        result1 = await port_allocator.reserve_port("service1", preferred_port=8080)
        assert result1.success is True
        assert result1.port == 8080
        
        # Second service should get different port
        result2 = await port_allocator.reserve_port("service2", preferred_port=8080)
        assert result2.success is True
        assert result2.port != 8080  # Different port allocated
        
        # Confirm allocations
        await port_allocator.confirm_allocation(result1.port, "service1", 12345)
        await port_allocator.confirm_allocation(result2.port, "service2", 12346)
        
        # Verify allocation tracking
        service1_ports = port_allocator.get_service_ports("service1")
        service2_ports = port_allocator.get_service_ports("service2")
        
        assert result1.port in service1_ports
        assert result2.port in service2_ports
        assert len(service1_ports & service2_ports) == 0  # No overlaps
    
    @pytest.mark.asyncio
    async def test_service_registry_handles_timing_issues(self, service_registry):
        """Test service registry with retry logic handles timing issues."""
        # This addresses test_09_service_discovery_timing_issues
        
        # Try to discover service that doesn't exist yet
        query = DiscoveryQuery(
            service_name="backend",
            timeout=5.0,
            retry_count=3,
            retry_delay=0.5
        )
        
        # Start discovery in background
        discovery_task = asyncio.create_task(
            service_registry.discover_service(query)
        )
        
        # Wait a bit, then register the service
        await asyncio.sleep(1.0)
        
        endpoints = [ServiceEndpoint(
            name="api",
            url="http://localhost:8000",
            port=8000
        )]
        
        await service_registry.register_service("backend", endpoints)
        await service_registry.update_service_status("backend", ServiceStatus.READY)
        
        # Discovery should eventually succeed
        result = await discovery_task
        assert result is not None
        assert result.service_name == "backend"
        assert result.status == ServiceStatus.READY
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_optional_services(self, service_coordinator):
        """Test graceful degradation when optional services fail."""
        # This addresses test_10_graceful_degradation_optional_services
        
        # Register services with some that will fail
        async def successful_startup():
            return {"success": True, "process_id": 12345}
        
        async def failing_startup():
            raise RuntimeError("Service failed to start")
        
        # Register required services (should succeed)
        service_coordinator.register_service(
            "database",
            startup_callback=successful_startup,
            readiness_checker=lambda: True
        )
        
        service_coordinator.register_service(
            "backend", 
            startup_callback=successful_startup,
            readiness_checker=lambda: True
        )
        
        # Register optional services (will fail)
        service_coordinator.register_service(
            "redis",
            startup_callback=failing_startup,
            readiness_checker=lambda: False
        )
        
        service_coordinator.register_service(
            "auth",
            startup_callback=failing_startup, 
            readiness_checker=lambda: False
        )
        
        # Start coordination
        services_to_start = ["database", "backend", "redis", "auth"]
        success = await service_coordinator.coordinate_startup(services_to_start)
        
        # Should succeed because required services started
        assert success is True
        
        # Check degraded services
        degraded = service_coordinator.get_degraded_services()
        assert "redis" in degraded
        assert "auth" in degraded
        
        # System should still be healthy
        assert service_coordinator.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_complete_coordination_workflow(
        self, 
        service_coordinator,
        dependency_manager,
        readiness_manager,
        port_allocator,
        service_registry
    ):
        """Test complete end-to-end coordination workflow."""
        
        # Setup mock services
        mock_processes = {}
        
        async def start_database():
            # Mock: Database isolation for unit testing without external database connections
            mock_processes["database"] = MagicMock()
            mock_processes["database"].pid = 1001
            return {"process": mock_processes["database"], "port": 5432}
        
        async def start_backend():
            # Reserve port first
            result = await port_allocator.reserve_port("backend", preferred_port=8000)
            assert result.success
            
            # Mock: Generic component isolation for controlled unit testing
            mock_processes["backend"] = MagicMock()
            mock_processes["backend"].pid = 1002
            
            # Register in service registry
            endpoints = [ServiceEndpoint("api", f"http://localhost:{result.port}", result.port)]
            await service_registry.register_service("backend", endpoints)
            
            return {"process": mock_processes["backend"], "port": result.port}
        
        async def start_frontend():
            result = await port_allocator.reserve_port("frontend", preferred_port=3000)
            assert result.success
            
            # Mock: Generic component isolation for controlled unit testing
            mock_processes["frontend"] = MagicMock()
            mock_processes["frontend"].pid = 1003
            
            endpoints = [ServiceEndpoint("web", f"http://localhost:{result.port}", result.port)]
            await service_registry.register_service("frontend", endpoints)
            
            return {"process": mock_processes["frontend"], "port": result.port}
        
        # Register readiness checkers
        # Mock: Database access isolation for fast, reliable unit testing
        readiness_manager.register_checker("database", AsyncMock(return_value=True))
        # Mock: Async component isolation for testing without real async operations
        readiness_manager.register_checker("backend", AsyncMock(return_value=True))
        # Mock: Async component isolation for testing without real async operations
        readiness_manager.register_checker("frontend", AsyncMock(return_value=True))
        
        # Register services with coordinator
        service_coordinator.register_service(
            "database",
            startup_callback=start_database,
            readiness_checker=lambda: readiness_manager.check_service_ready("database")
        )
        
        service_coordinator.register_service(
            "backend",
            startup_callback=start_backend,
            readiness_checker=lambda: readiness_manager.check_service_ready("backend"),
            dependencies=[ServiceDependency("backend", "database", DependencyType.REQUIRED)]
        )
        
        service_coordinator.register_service(
            "frontend",
            startup_callback=start_frontend,
            readiness_checker=lambda: readiness_manager.check_service_ready("frontend"),
            dependencies=[ServiceDependency("frontend", "backend", DependencyType.REQUIRED)]
        )
        
        # Start coordination
        success = await service_coordinator.coordinate_startup(["database", "backend", "frontend"])
        
        # Verify success
        assert success is True
        
        # Verify all services started
        status = service_coordinator.get_startup_status()
        assert status["coordination_state"] == CoordinationState.COMPLETED.value
        
        for service_name in ["database", "backend", "frontend"]:
            assert status["services"][service_name]["startup_success"] is True
            assert status["services"][service_name]["dependency_state"] == "ready"
        
        # Verify service registry has all services
        all_services = await service_registry.discover_services(DiscoveryQuery())
        service_names = {s.service_name for s in all_services}
        assert "backend" in service_names
        assert "frontend" in service_names
        
        # Verify port allocations
        allocation_summary = port_allocator.get_allocation_summary()
        assert len(allocation_summary["allocated_ports"]) >= 2  # backend and frontend
    
    @pytest.mark.asyncio
    async def test_coordination_failure_recovery(self, service_coordinator):
        """Test coordination system handles failures gracefully."""
        
        failure_count = 0
        
        async def flaky_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise RuntimeError(f"Service failed attempt {failure_count}")
            return {"success": True, "process_id": 9999}
        
        # Register flaky service
        service_coordinator.register_service(
            "flaky_service",
            startup_callback=flaky_service,
            readiness_checker=lambda: True
        )
        
        # Start coordination - should succeed after retries
        success = await service_coordinator.coordinate_startup(["flaky_service"])
        
        # Should eventually succeed
        assert success is True
        assert failure_count == 3  # Failed twice, succeeded on third attempt
        
        # Verify final state
        status = service_coordinator.get_startup_status()
        assert status["services"]["flaky_service"]["startup_success"] is True
    
    @pytest.mark.asyncio
    async def test_port_reservation_timeout_cleanup(self, port_allocator):
        """Test port reservations are cleaned up after timeout."""
        
        # Set short timeout
        port_allocator.default_reservation_timeout = 0.5
        
        # Reserve port
        result = await port_allocator.reserve_port("test_service", preferred_port=9999)
        assert result.success is True
        
        # Verify reservation exists
        port_status = port_allocator.get_port_status(9999)
        assert port_status is not None
        assert port_status.service_name == "test_service"
        
        # Wait for timeout + cleanup cycle
        await asyncio.sleep(1.5)
        
        # Force cleanup
        await port_allocator._cleanup_expired_reservations()
        
        # Verify reservation was cleaned up
        port_status = port_allocator.get_port_status(9999)
        assert port_status is None
        
        # Should be able to reserve again
        result2 = await port_allocator.reserve_port("other_service", preferred_port=9999)
        assert result2.success is True
        assert result2.port == 9999
    
    @pytest.mark.asyncio
    async def test_service_registry_persistence(self, temp_registry_dir):
        """Test service registry persistence across restarts."""
        
        # Create first registry instance
        registry1 = ServiceRegistry(registry_dir=temp_registry_dir, enable_persistence=True)
        await registry1.start()
        
        # Register service
        endpoints = [ServiceEndpoint("api", "http://localhost:8080", 8080)]
        await registry1.register_service("test_service", endpoints, metadata={"test": "data"})
        await registry1.update_service_status("test_service", ServiceStatus.READY)
        
        # Stop registry
        await registry1.stop()
        
        # Create second registry instance (simulates restart)
        registry2 = ServiceRegistry(registry_dir=temp_registry_dir, enable_persistence=True)
        await registry2.start()
        
        # Should load persisted service
        query = DiscoveryQuery(service_name="test_service")
        service = await registry2.discover_service(query)
        
        assert service is not None
        assert service.service_name == "test_service"
        assert service.metadata.get("test") == "data"
        
        await registry2.stop()


class TestCoordinationSystemPerformance:
    """Performance tests for coordination system."""
    
    @pytest.mark.asyncio
    async def test_large_scale_coordination(self):
        """Test coordination with many services."""
        
        coordinator = ServiceCoordinator(CoordinationConfig(
            max_parallel_starts=5,
            dependency_timeout=10,
            readiness_timeout=10
        ))
        
        # Create many mock services
        service_count = 20
        
        async def quick_startup():
            await asyncio.sleep(0.1)  # Simulate quick startup
            return {"success": True}
        
        # Register services
        for i in range(service_count):
            coordinator.register_service(
                f"service_{i}",
                startup_callback=quick_startup,
                readiness_checker=lambda: True
            )
        
        # Time the coordination
        start_time = time.time()
        service_names = [f"service_{i}" for i in range(service_count)]
        success = await coordinator.coordinate_startup(service_names)
        end_time = time.time()
        
        # Should complete successfully
        assert success is True
        
        # Should complete in reasonable time (parallel execution)
        duration = end_time - start_time
        assert duration < 5.0  # Should be much faster than sequential
        
        logger.info(f"Coordinated {service_count} services in {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_port_allocation_performance(self):
        """Test port allocation performance under load."""
        
        allocator = PortAllocator()
        await allocator.start()
        
        try:
            # Allocate many ports concurrently
            port_count = 100
            
            async def allocate_port(service_id):
                result = await allocator.reserve_port(f"service_{service_id}")
                assert result.success is True
                return result.port
            
            start_time = time.time()
            tasks = [allocate_port(i) for i in range(port_count)]
            ports = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Verify all allocations
            assert len(ports) == port_count
            assert len(set(ports)) == port_count  # All unique ports
            
            duration = end_time - start_time
            logger.info(f"Allocated {port_count} ports in {duration:.2f}s")
            
            # Should be reasonably fast
            assert duration < 5.0
            
        finally:
            await allocator.stop()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])