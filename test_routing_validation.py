#!/usr/bin/env python3
"""Simple test to validate routing module fixes"""

import asyncio
import sys
sys.path.insert(0, './netra_backend')

from netra_backend.app.services.api_gateway.load_balancer import LoadBalancer, ServiceEndpoint
from netra_backend.app.services.api_gateway.route_manager import RouteManager
from netra_backend.app.services.api_gateway.router import ApiGatewayRouter
from netra_backend.app.services.service_discovery.discovery_service import ServiceDiscoveryService

async def test_routing_components():
    """Test that our routing components work."""
    
    # Test LoadBalancer
    load_balancer = LoadBalancer()
    await load_balancer.initialize()
    
    endpoints = [
        ServiceEndpoint("localhost", 8001, 1, "healthy"),
        ServiceEndpoint("localhost", 8002, 1, "healthy")
    ]
    
    load_balancer.register_service("test_service", endpoints)
    endpoint = await load_balancer.get_endpoint("test_service", "round_robin")
    assert endpoint is not None
    assert endpoint.host == "localhost"
    print("PASS: LoadBalancer works")
    
    # Test RouteManager
    route_manager = RouteManager()
    await route_manager.initialize()
    await route_manager.shutdown()
    print("PASS: RouteManager works")
    
    # Test ApiGatewayRouter
    router = ApiGatewayRouter()
    await router.initialize()
    
    route_result = await router.find_route("/api/v1/users")
    assert route_result is not None
    assert route_result["rule"].service_name == "user_service"
    print("PASS: ApiGatewayRouter works")
    
    await router.shutdown()
    
    # Test ServiceDiscoveryService
    service_discovery = ServiceDiscoveryService()
    await service_discovery.initialize()
    
    await service_discovery.register_service("test_service", endpoints)
    service = service_discovery.get_service("test_service")
    assert service is not None
    print("PASS: ServiceDiscoveryService works")
    
    await service_discovery.shutdown()
    await load_balancer.shutdown()
    
    print("All routing components are working correctly!")

if __name__ == "__main__":
    asyncio.run(test_routing_components())