"""
L3-12: Service Discovery with Real Health Checks Integration Test

BVJ: Critical for multi-service orchestration and ensuring system reliability.
Service discovery enables dynamic scaling and automatic failover.

Tests service discovery with real health checks using Docker containers.
"""

import pytest
import asyncio
import docker
import time
import aiohttp
import json
from typing import Dict, Any, List, Optional
from app.discovery.service_registry import ServiceRegistry
from app.discovery.health_checker import HealthChecker
from app.discovery.consul_client import ConsulClient


@pytest.mark.L3
class TestServiceDiscoveryHealthChecksL3:
    """Test service discovery with real health checks."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def consul_container(self, docker_client):
        """Start Consul container for service discovery."""
        container = docker_client.containers.run(
            "consul:latest",
            command="agent -dev -client=0.0.0.0",
            ports={'8500/tcp': None},
            detach=True,
            name="consul_test_container"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['8500/tcp'][0]['HostPort']
        
        # Wait for Consul to be ready
        await self._wait_for_consul(port)
        
        consul_config = {
            "host": "localhost",
            "port": int(port)
        }
        
        yield consul_config
        
        container.stop()
        container.remove()
    
    @pytest.fixture(scope="class")
    async def test_services(self, docker_client):
        """Start test service containers."""
        services = {}
        
        # Start nginx service (healthy)
        nginx_container = docker_client.containers.run(
            "nginx:alpine",
            ports={'80/tcp': None},
            detach=True,
            name="test_service_nginx"
        )
        
        nginx_container.reload()
        nginx_port = nginx_container.attrs['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
        
        services["nginx"] = {
            "container": nginx_container,
            "url": f"http://localhost:{nginx_port}",
            "port": int(nginx_port)
        }
        
        # Start echo service (will be healthy/unhealthy for testing)
        echo_container = docker_client.containers.run(
            "hashicorp/http-echo:latest",
            command=["-text=echo service running"],
            ports={'5678/tcp': None},
            detach=True,
            name="test_service_echo"
        )
        
        echo_container.reload()
        echo_port = echo_container.attrs['NetworkSettings']['Ports']['5678/tcp'][0]['HostPort']
        
        services["echo"] = {
            "container": echo_container,
            "url": f"http://localhost:{echo_port}",
            "port": int(echo_port)
        }
        
        # Wait for services to be ready
        await self._wait_for_service(services["nginx"]["url"])
        await self._wait_for_service(services["echo"]["url"])
        
        yield services
        
        # Cleanup
        for service_name, service_info in services.items():
            service_info["container"].stop()
            service_info["container"].remove()
    
    async def _wait_for_consul(self, port: str, timeout: int = 30):
        """Wait for Consul to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{port}/v1/status/leader",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Consul not ready within {timeout}s")
    
    async def _wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Service at {url} not ready within {timeout}s")
    
    @pytest.fixture
    async def service_registry(self, consul_container):
        """Create service registry with Consul backend."""
        registry = ServiceRegistry(consul_config=consul_container)
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.fixture
    async def health_checker(self, consul_container):
        """Create health checker."""
        checker = HealthChecker(consul_config=consul_container)
        await checker.initialize()
        yield checker
        await checker.stop()
    
    @pytest.mark.asyncio
    async def test_service_registration_and_discovery(
        self, 
        service_registry, 
        test_services
    ):
        """Test basic service registration and discovery."""
        # Register nginx service
        nginx_service = {
            "name": "nginx-service",
            "id": "nginx-1",
            "address": "localhost",
            "port": test_services["nginx"]["port"],
            "tags": ["web", "frontend"],
            "meta": {"version": "1.0"}
        }
        
        registration_result = await service_registry.register_service(nginx_service)
        assert registration_result["success"] is True
        
        # Discover the service
        discovered_services = await service_registry.discover_services("nginx-service")
        
        assert len(discovered_services) == 1
        assert discovered_services[0]["name"] == "nginx-service"
        assert discovered_services[0]["address"] == "localhost"
        assert discovered_services[0]["port"] == test_services["nginx"]["port"]
        assert "web" in discovered_services[0]["tags"]
    
    @pytest.mark.asyncio
    async def test_service_health_check_integration(
        self, 
        service_registry, 
        health_checker, 
        test_services
    ):
        """Test service health check integration."""
        # Register nginx service with health check
        nginx_service = {
            "name": "nginx-health",
            "id": "nginx-health-1",
            "address": "localhost",
            "port": test_services["nginx"]["port"],
            "health_check": {
                "http": test_services["nginx"]["url"],
                "interval": "1s",
                "timeout": "500ms"
            }
        }
        
        await service_registry.register_service(nginx_service)
        
        # Start health checking
        health_task = asyncio.create_task(health_checker.start())
        
        # Wait for health checks to run
        await asyncio.sleep(3)
        
        # Check service health status
        health_status = await service_registry.get_service_health("nginx-health-1")
        
        assert health_status["service_id"] == "nginx-health-1"
        assert health_status["status"] == "healthy"
        
        # Stop health checker
        await health_checker.stop()
        health_task.cancel()
    
    @pytest.mark.asyncio
    async def test_unhealthy_service_detection(
        self, 
        service_registry, 
        health_checker, 
        test_services
    ):
        """Test detection and handling of unhealthy services."""
        # Register echo service
        echo_service = {
            "name": "echo-service",
            "id": "echo-1",
            "address": "localhost",
            "port": test_services["echo"]["port"],
            "health_check": {
                "http": test_services["echo"]["url"],
                "interval": "500ms",
                "timeout": "200ms"
            }
        }
        
        await service_registry.register_service(echo_service)
        
        # Start health checking
        health_task = asyncio.create_task(health_checker.start())
        
        # Wait for initial healthy status
        await asyncio.sleep(2)
        initial_health = await service_registry.get_service_health("echo-1")
        assert initial_health["status"] == "healthy"
        
        # Stop the echo service to make it unhealthy
        test_services["echo"]["container"].stop()
        
        # Wait for health check to detect failure
        await asyncio.sleep(3)
        
        # Check service is now unhealthy
        unhealthy_status = await service_registry.get_service_health("echo-1")
        assert unhealthy_status["status"] == "unhealthy"
        
        # Verify service is excluded from discovery
        healthy_services = await service_registry.discover_healthy_services("echo-service")
        assert len(healthy_services) == 0
        
        # Stop health checker
        await health_checker.stop()
        health_task.cancel()
    
    @pytest.mark.asyncio
    async def test_service_load_balancing(
        self, 
        service_registry, 
        test_services
    ):
        """Test service load balancing across multiple instances."""
        # Register multiple instances of the same service
        for i in range(3):
            service = {
                "name": "loadbalanced-service",
                "id": f"lb-service-{i}",
                "address": "localhost",
                "port": test_services["nginx"]["port"] + i,  # Different ports
                "tags": ["api", "backend"],
                "weight": i + 1  # Different weights
            }
            await service_registry.register_service(service)
        
        # Test round-robin load balancing
        selected_services = []
        for _ in range(6):  # Get 6 services to see round-robin pattern
            service = await service_registry.get_service_instance(
                "loadbalanced-service",
                strategy="round_robin"
            )
            selected_services.append(service["id"])
        
        # Should cycle through all instances
        unique_services = set(selected_services)
        assert len(unique_services) == 3
        
        # Test weighted load balancing
        weighted_selections = []
        for _ in range(100):  # Large sample for weighted distribution
            service = await service_registry.get_service_instance(
                "loadbalanced-service",
                strategy="weighted"
            )
            weighted_selections.append(service["id"])
        
        # Higher weight services should be selected more often
        lb_service_2_count = weighted_selections.count("lb-service-2")
        lb_service_0_count = weighted_selections.count("lb-service-0")
        
        assert lb_service_2_count > lb_service_0_count  # Weight 3 > Weight 1
    
    @pytest.mark.asyncio
    async def test_service_auto_deregistration(
        self, 
        service_registry, 
        health_checker, 
        test_services
    ):
        """Test automatic service deregistration on failure."""
        # Register service with auto-deregister policy
        service = {
            "name": "auto-dereg-service",
            "id": "auto-dereg-1",
            "address": "localhost",
            "port": test_services["echo"]["port"],
            "health_check": {
                "http": test_services["echo"]["url"],
                "interval": "500ms",
                "timeout": "200ms",
                "deregister_critical_service_after": "2s"
            }
        }
        
        await service_registry.register_service(service)
        
        # Start health checking
        health_task = asyncio.create_task(health_checker.start())
        
        # Verify service is registered
        services = await service_registry.discover_services("auto-dereg-service")
        assert len(services) == 1
        
        # Stop the service to trigger failure
        test_services["echo"]["container"].stop()
        
        # Wait for auto-deregistration (2s + some buffer)
        await asyncio.sleep(4)
        
        # Verify service was automatically deregistered
        services_after = await service_registry.discover_services("auto-dereg-service")
        assert len(services_after) == 0
        
        # Stop health checker
        await health_checker.stop()
        health_task.cancel()
    
    @pytest.mark.asyncio
    async def test_service_metadata_and_tags(
        self, 
        service_registry, 
        test_services
    ):
        """Test service discovery with metadata and tag filtering."""
        # Register services with different tags and metadata
        services_to_register = [
            {
                "name": "api-service",
                "id": "api-v1",
                "address": "localhost",
                "port": test_services["nginx"]["port"],
                "tags": ["api", "v1", "production"],
                "meta": {"version": "1.0", "environment": "prod"}
            },
            {
                "name": "api-service",
                "id": "api-v2",
                "address": "localhost",
                "port": test_services["echo"]["port"],
                "tags": ["api", "v2", "beta"],
                "meta": {"version": "2.0", "environment": "staging"}
            }
        ]
        
        for service in services_to_register:
            await service_registry.register_service(service)
        
        # Discover services by tag
        v1_services = await service_registry.discover_services_by_tag("v1")
        assert len(v1_services) == 1
        assert v1_services[0]["id"] == "api-v1"
        
        production_services = await service_registry.discover_services_by_tag("production")
        assert len(production_services) == 1
        assert production_services[0]["meta"]["environment"] == "prod"
        
        # Discover services by metadata
        staging_services = await service_registry.discover_services_by_meta(
            "environment", "staging"
        )
        assert len(staging_services) == 1
        assert staging_services[0]["id"] == "api-v2"
    
    @pytest.mark.asyncio
    async def test_service_watch_and_notifications(
        self, 
        service_registry, 
        test_services
    ):
        """Test service watch functionality and change notifications."""
        notifications = []
        
        async def service_change_handler(event_type, service_data):
            notifications.append({
                "type": event_type,
                "service": service_data
            })
        
        # Start watching for service changes
        watch_task = asyncio.create_task(
            service_registry.watch_services("watched-service", service_change_handler)
        )
        
        # Give watch some time to start
        await asyncio.sleep(0.5)
        
        # Register a service (should trigger notification)
        service = {
            "name": "watched-service",
            "id": "watched-1",
            "address": "localhost",
            "port": test_services["nginx"]["port"]
        }
        
        await service_registry.register_service(service)
        await asyncio.sleep(0.5)
        
        # Deregister the service (should trigger notification)
        await service_registry.deregister_service("watched-1")
        await asyncio.sleep(0.5)
        
        # Stop watching
        watch_task.cancel()
        
        # Verify notifications were received
        assert len(notifications) >= 2
        
        # Check for registration notification
        register_notifications = [n for n in notifications if n["type"] == "register"]
        assert len(register_notifications) >= 1
        assert register_notifications[0]["service"]["id"] == "watched-1"
        
        # Check for deregistration notification
        deregister_notifications = [n for n in notifications if n["type"] == "deregister"]
        assert len(deregister_notifications) >= 1
    
    @pytest.mark.asyncio
    async def test_cross_datacenter_service_discovery(
        self, 
        service_registry, 
        test_services
    ):
        """Test service discovery across multiple datacenters."""
        # Register services in different datacenters
        dc1_service = {
            "name": "multi-dc-service",
            "id": "mdc-dc1-1",
            "address": "localhost",
            "port": test_services["nginx"]["port"],
            "datacenter": "dc1",
            "tags": ["primary"]
        }
        
        dc2_service = {
            "name": "multi-dc-service",
            "id": "mdc-dc2-1",
            "address": "localhost",
            "port": test_services["echo"]["port"],
            "datacenter": "dc2",
            "tags": ["secondary"]
        }
        
        await service_registry.register_service(dc1_service)
        await service_registry.register_service(dc2_service)
        
        # Discover services in specific datacenter
        dc1_services = await service_registry.discover_services_in_datacenter(
            "multi-dc-service", "dc1"
        )
        assert len(dc1_services) == 1
        assert dc1_services[0]["datacenter"] == "dc1"
        
        dc2_services = await service_registry.discover_services_in_datacenter(
            "multi-dc-service", "dc2"
        )
        assert len(dc2_services) == 1
        assert dc2_services[0]["datacenter"] == "dc2"
        
        # Discover services across all datacenters
        all_services = await service_registry.discover_services("multi-dc-service")
        assert len(all_services) == 2