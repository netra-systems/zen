"""

E2E Tests for Service Coordination - Initialization Gates and Port Allocation

Business Value: Validates reliable service startup and port management

"""



import asyncio

import platform

import pytest

import socket

from typing import Dict, List

from shared.isolated_environment import IsolatedEnvironment



from dev_launcher.service_coordination import (

    ServiceCoordinator,

    PlatformAwarePortAllocator,

    ServiceDependency,

    ServiceState,

    PortAllocationStrategy,

    initialize_services_with_gates,

    get_service_coordinator

)





@pytest.mark.e2e

class TestPlatformAwarePortAllocator:

    """Test platform-aware port allocation."""

    

    @pytest.fixture

    def allocator(self):

        """Create a port allocator instance."""

        return PlatformAwarePortAllocator()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_preferred_port(self, allocator):

        """Test allocating a preferred port when available."""

        port = await allocator.allocate_port("test_service", preferred_port=9999)

        assert port == 9999

        assert "test_service" in allocator.service_port_map

        assert allocator.service_port_map["test_service"] == 9999

        assert 9999 in allocator.allocated_ports

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_service_specific_port(self, allocator):

        """Test allocating from service-specific preferred ports."""

        # Backend should get one of its preferred ports

        port = await allocator.allocate_port("backend")

        assert port in [8000, 8001, 8002] or port > 1024

        assert "backend" in allocator.service_port_map

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_dynamic_port(self, allocator):

        """Test dynamic port allocation."""

        port = await allocator.allocate_port(

            "custom_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        assert port > 1024

        assert "custom_service" in allocator.service_port_map

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_ephemeral_port(self, allocator):

        """Test ephemeral port allocation."""

        port = await allocator.allocate_port(

            "ephemeral_service",

            strategy=PortAllocationStrategy.EPHEMERAL

        )

        assert port > 1024

        assert "ephemeral_service" in allocator.service_port_map

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_port_conflict_resolution(self, allocator):

        """Test handling of port conflicts."""

        # Allocate a port

        port1 = await allocator.allocate_port("service1", preferred_port=8888)

        assert port1 == 8888

        

        # Try to allocate same port - should get different one

        port2 = await allocator.allocate_port("service2", preferred_port=8888)

        assert port2 != 8888

        assert port2 > 1024

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_release_port(self, allocator):

        """Test releasing allocated ports."""

        port = await allocator.allocate_port("test_service", preferred_port=7777)

        assert port == 7777

        assert 7777 in allocator.allocated_ports

        

        await allocator.release_port("test_service")

        assert "test_service" not in allocator.service_port_map

        assert 7777 not in allocator.allocated_ports

        

        # Should be able to allocate the port again

        port2 = await allocator.allocate_port("another_service", preferred_port=7777)

        assert port2 == 7777

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_platform_specific_ranges(self, allocator):

        """Test platform-specific port ranges."""

        current_platform = platform.system()

        

        if current_platform == "Windows":

            expected_range = (49152, 65535)

        elif current_platform == "Darwin":

            expected_range = (49152, 65535)

        elif current_platform == "Linux":

            expected_range = (32768, 60999)

        else:

            expected_range = (49152, 65535)  # Default

        

        assert allocator.PLATFORM_PORT_RANGES.get(current_platform, (49152, 65535)) == expected_range

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_allocation(self, allocator):

        """Test concurrent port allocation."""

        tasks = []

        for i in range(10):

            tasks.append(

                allocator.allocate_port(f"service_{i}")

            )

        

        ports = await asyncio.gather(*tasks)

        

        # All ports should be unique

        assert len(set(ports)) == 10

        

        # All services should be in the map

        for i in range(10):

            assert f"service_{i}" in allocator.service_port_map

    

    @pytest.mark.e2e

    def test_get_allocation_summary(self, allocator):

        """Test getting allocation summary."""

        summary = allocator.get_allocation_summary()

        

        assert "platform" in summary

        assert summary["platform"] == platform.system()

        assert "allocated_ports" in summary

        assert "service_ports" in summary

        assert "port_range" in summary





@pytest.mark.e2e

class TestServiceInitializationGates:

    """Test service initialization with dependency gates."""

    

    @pytest.fixture

    def coordinator(self):

        """Create a service coordinator instance."""

        return ServiceCoordinator()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_register_service(self, coordinator):

        """Test registering a service."""

        gate = await coordinator.register_service(

            "test_service",

            health_check_endpoint="/health"

        )

        

        assert gate.service_name == "test_service"

        assert gate.state == ServiceState.UNINITIALIZED

        assert gate.health_check_endpoint == "/health"

        assert len(gate.dependencies) == 0

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_register_service_with_dependencies(self, coordinator):

        """Test registering a service with dependencies."""

        deps = [

            ServiceDependency("database", required=True),

            ServiceDependency("cache", required=False)

        ]

        

        gate = await coordinator.register_service(

            "api_service",

            dependencies=deps

        )

        

        assert len(gate.dependencies) == 2

        assert gate.dependencies[0].service_name == "database"

        assert gate.dependencies[0].required == True

        assert gate.dependencies[1].service_name == "cache"

        assert gate.dependencies[1].required == False

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_service_no_deps(self, coordinator):

        """Test initializing a service without dependencies."""

        await coordinator.register_service("standalone_service")

        

        success, port = await coordinator.initialize_service("standalone_service")

        

        assert success == True

        assert port is not None

        assert port > 1024

        

        gate = coordinator.services["standalone_service"]

        assert gate.state == ServiceState.READY

        assert gate.init_start_time is not None

        assert gate.init_end_time is not None

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_service_with_deps(self, coordinator):

        """Test initializing a service with dependencies."""

        # Register database service

        await coordinator.register_service("database")

        

        # Register API service that depends on database

        deps = [ServiceDependency("database", required=True)]

        await coordinator.register_service("api", dependencies=deps)

        

        # Initialize database first

        db_success, db_port = await coordinator.initialize_service("database")

        assert db_success == True

        

        # Now initialize API

        api_success, api_port = await coordinator.initialize_service("api")

        assert api_success == True

        assert api_port != db_port

        

        # Check initialization order

        assert coordinator._initialization_order == ["database", "api"]

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_service_missing_required_dep(self, coordinator):

        """Test initialization fails when required dependency is missing."""

        deps = [ServiceDependency("missing_service", required=True)]

        await coordinator.register_service("dependent_service", dependencies=deps)

        

        success, port = await coordinator.initialize_service("dependent_service")

        

        assert success == False

        assert port is None

        

        gate = coordinator.services["dependent_service"]

        assert gate.state == ServiceState.FAILED

        assert "Dependencies failed" in gate.error_message

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_service_optional_dep_missing(self, coordinator):

        """Test initialization succeeds when optional dependency is missing."""

        deps = [ServiceDependency("optional_service", required=False)]

        await coordinator.register_service("flexible_service", dependencies=deps)

        

        success, port = await coordinator.initialize_service("flexible_service")

        

        assert success == True

        assert port is not None

        

        gate = coordinator.services["flexible_service"]

        assert gate.state == ServiceState.READY

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_already_initialized(self, coordinator):

        """Test initializing an already initialized service."""

        await coordinator.register_service("test_service")

        

        # First initialization

        success1, port1 = await coordinator.initialize_service("test_service")

        assert success1 == True

        

        # Second initialization - should return same port

        success2, port2 = await coordinator.initialize_service("test_service")

        assert success2 == True

        assert port2 == port1

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_stop_service(self, coordinator):

        """Test stopping a service."""

        await coordinator.register_service("test_service")

        success, port = await coordinator.initialize_service("test_service")

        assert success == True

        

        await coordinator.stop_service("test_service")

        

        gate = coordinator.services["test_service"]

        assert gate.state == ServiceState.STOPPED

        assert "test_service" not in coordinator.port_allocator.service_port_map

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_stop_all_services(self, coordinator):

        """Test stopping all services in reverse order."""

        # Initialize services

        await coordinator.register_service("service1")

        await coordinator.register_service("service2")

        await coordinator.register_service("service3")

        

        await coordinator.initialize_service("service1")

        await coordinator.initialize_service("service2")

        await coordinator.initialize_service("service3")

        

        assert coordinator._initialization_order == ["service1", "service2", "service3"]

        

        await coordinator.stop_all_services()

        

        # All services should be stopped

        for service_name in ["service1", "service2", "service3"]:

            assert coordinator.services[service_name].state == ServiceState.STOPPED

    

    @pytest.mark.e2e

    def test_get_initialization_summary(self, coordinator):

        """Test getting initialization summary."""

        summary = coordinator.get_initialization_summary()

        

        assert "total_services" in summary

        assert "ready" in summary

        assert "failed" in summary

        assert "pending" in summary

        assert "services" in summary

        assert "initialization_order" in summary

        assert "port_allocation" in summary





@pytest.mark.e2e

class TestIntegratedServiceCoordination:

    """Test integrated service coordination scenarios."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_initialize_services_with_gates(self):

        """Test initializing multiple services with gates."""

        services = [

            {

                "name": "database",

                "depends_on": [],

                "health_endpoint": "/health",

                "port_config": {"preferred_port": 5432}

            },

            {

                "name": "cache",

                "depends_on": [],

                "health_endpoint": "/ping",

                "port_config": {"preferred_port": 6379}

            },

            {

                "name": "backend",

                "depends_on": ["database", "cache"],

                "health_endpoint": "/api/health",

                "port_config": {"strategy": "dynamic"}

            },

            {

                "name": "frontend",

                "depends_on": ["backend"],

                "health_endpoint": "/",

                "port_config": {"preferred_port": 3000}

            }

        ]

        

        summary = await initialize_services_with_gates(services, parallel=True)

        

        assert summary["ready"] == 4

        assert summary["failed"] == 0

        assert len(summary["initialization_order"]) == 4

        

        # Check dependencies were respected

        db_index = summary["initialization_order"].index("database")

        cache_index = summary["initialization_order"].index("cache")

        backend_index = summary["initialization_order"].index("backend")

        frontend_index = summary["initialization_order"].index("frontend")

        

        assert db_index < backend_index

        assert cache_index < backend_index

        assert backend_index < frontend_index

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_parallel_vs_sequential_initialization(self):

        """Test parallel vs sequential initialization."""

        services = [

            {"name": "service1", "depends_on": []},

            {"name": "service2", "depends_on": []},

            {"name": "service3", "depends_on": []},

        ]

        

        # Reset coordinator

        global _coordinator

        from dev_launcher import service_coordination

        service_coordination._coordinator = None

        

        # Parallel initialization

        summary_parallel = await initialize_services_with_gates(services, parallel=True)

        assert summary_parallel["ready"] == 3

        

        # Reset coordinator

        service_coordination._coordinator = None

        

        # Sequential initialization

        summary_sequential = await initialize_services_with_gates(services, parallel=False)

        assert summary_sequential["ready"] == 3

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_complex_dependency_graph(self):

        """Test complex service dependency graph."""

        # Reset coordinator for fresh test

        global _coordinator

        from dev_launcher import service_coordination

        service_coordination._coordinator = None

        

        services = [

            {"name": "db", "depends_on": []},

            {"name": "cache", "depends_on": []},

            {"name": "auth", "depends_on": ["db"]},

            {"name": "api", "depends_on": ["db", "cache", "auth"]},

            {"name": "worker", "depends_on": ["db", "cache"]},

            {"name": "frontend", "depends_on": ["api", "auth"]},

            {"name": "admin", "depends_on": ["api", "auth", "db"]},

        ]

        

        summary = await initialize_services_with_gates(services, parallel=True)

        

        assert summary["ready"] == 7

        assert summary["failed"] == 0

        

        # Verify dependency ordering

        order = summary["initialization_order"]

        

        # db and cache should be before everything else

        assert order.index("db") < order.index("auth")

        assert order.index("db") < order.index("api")

        assert order.index("cache") < order.index("api")

        assert order.index("auth") < order.index("api")

        assert order.index("api") < order.index("frontend")

        assert order.index("api") < order.index("admin")

    

    @pytest.mark.e2e

    def test_get_service_coordinator_singleton(self):

        """Test that get_service_coordinator returns singleton."""

        coord1 = get_service_coordinator()

        coord2 = get_service_coordinator()

        assert coord1 is coord2





@pytest.mark.e2e

class TestPortAvailabilityChecking:

    """Test port availability checking logic."""

    

    @pytest.fixture

    def allocator(self):

        """Create a port allocator instance."""

        return PlatformAwarePortAllocator()

    

    @pytest.mark.e2e

    def test_is_port_available_free_port(self, allocator):

        """Test checking a free port."""

        # Find a likely free port

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

            sock.bind(('', 0))

            free_port = sock.getsockname()[1]

        

        # Should be available

        assert allocator._is_port_available(free_port) == True

    

    @pytest.mark.e2e

    def test_is_port_available_allocated_port(self, allocator):

        """Test checking an allocated port."""

        allocator.allocated_ports.add(12345)

        assert allocator._is_port_available(12345) == False

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_port_allocation_with_retry(self, allocator):

        """Test port allocation with retry logic."""

        # Mock to simulate port conflicts

        original_is_available = allocator._is_port_available

        call_count = 0

        

        def mock_is_available(port):

            nonlocal call_count

            call_count += 1

            # Fail first 3 attempts, then succeed

            if call_count <= 3:

                return False

            return original_is_available(port)

        

        allocator._is_port_available = mock_is_available

        

        port = await allocator._find_dynamic_port()

        assert port > 1024

        assert call_count > 3  # Should have retried

    

    @pytest.mark.e2e

    def test_get_ephemeral_port(self, allocator):

        """Test getting an ephemeral port from OS."""

        port = allocator._get_ephemeral_port()

        assert port > 1024

        assert port <= 65535

