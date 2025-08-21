"""API Request Routing Rules L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API routing infrastructure)
- Business Goal: Ensure correct request routing and load distribution
- Value Impact: Prevents routing failures, maintains service reliability
- Strategic Impact: $15K MRR protection through API gateway routing accuracy

Critical Path: Request ingress -> Route evaluation -> Service discovery -> Load balancing -> Request forwarding
Coverage: Complex routing rules, path matching, header-based routing, version routing, load balancing
"""

import pytest
import asyncio
import time
import uuid
import logging
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
from enum import Enum

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.api_gateway.router import ApiGatewayRouter
from netra_backend.app.services.api_gateway.route_manager import RouteManager
from netra_backend.app.services.api_gateway.load_balancer import LoadBalancer
from netra_backend.app.services.service_discovery.discovery_service import ServiceDiscoveryService

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class RouteRule:
    """Routing rule configuration."""
    path_pattern: str
    service_name: str
    load_balancing_strategy: str  # round_robin, weighted, least_connections
    health_check_path: str
    timeout_seconds: int
    retry_count: int
    priority: int  # Higher = more priority


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    host: str
    port: int
    weight: int  # For weighted load balancing
    health_status: str  # healthy, unhealthy, unknown


class ApiRoutingManager:
    """Manages L3 API routing tests with real HTTP routing."""
    
    def __init__(self):
        self.router = None
        self.route_manager = None
        self.load_balancer = None
        self.service_discovery = None
        self.test_servers = {}  # Mock backend services
        self.routing_rules = {}
        self.service_endpoints = {}
        self.routing_metrics = []
        self.failed_routes = []
        
    async def initialize_routing(self):
        """Initialize API routing services for L3 testing."""
        try:
            self.router = ApiGatewayRouter()
            await self.router.initialize()
            
            self.route_manager = RouteManager()
            await self.route_manager.initialize()
            
            self.load_balancer = LoadBalancer()
            await self.load_balancer.initialize()
            
            self.service_discovery = ServiceDiscoveryService()
            await self.service_discovery.initialize()
            
            # Setup test routing configuration
            await self.setup_routing_rules()
            await self.setup_backend_services()
            
            logger.info("API routing services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize API routing services: {e}")
            raise
    
    async def setup_routing_rules(self):
        """Configure complex routing rules for testing."""
        self.routing_rules = {
            # Exact path matching
            "/api/v1/users": RouteRule(
                path_pattern="/api/v1/users",
                service_name="user_service",
                load_balancing_strategy="round_robin",
                health_check_path="/health",
                timeout_seconds=30,
                retry_count=3,
                priority=10
            ),
            # Wildcard path matching
            "/api/v1/users/*": RouteRule(
                path_pattern="/api/v1/users/*",
                service_name="user_service",
                load_balancing_strategy="least_connections",
                health_check_path="/health",
                timeout_seconds=30,
                retry_count=2,
                priority=9
            ),
            # Regex pattern matching
            "/api/v1/threads/[0-9a-f-]+": RouteRule(
                path_pattern=r"/api/v1/threads/[0-9a-f-]+",
                service_name="thread_service",
                load_balancing_strategy="weighted",
                health_check_path="/health",
                timeout_seconds=45,
                retry_count=3,
                priority=8
            ),
            # Version-based routing
            "/api/v2/agents": RouteRule(
                path_pattern="/api/v2/agents",
                service_name="agent_service_v2",
                load_balancing_strategy="round_robin",
                health_check_path="/v2/health",
                timeout_seconds=60,
                retry_count=2,
                priority=7
            ),
            # Legacy version routing
            "/api/v1/agents": RouteRule(
                path_pattern="/api/v1/agents",
                service_name="agent_service_v1",
                load_balancing_strategy="round_robin",
                health_check_path="/health",
                timeout_seconds=30,
                retry_count=1,
                priority=6
            ),
            # Admin routes with higher priority
            "/api/admin/*": RouteRule(
                path_pattern="/api/admin/*",
                service_name="admin_service",
                load_balancing_strategy="least_connections",
                health_check_path="/admin/health",
                timeout_seconds=120,
                retry_count=5,
                priority=15
            )
        }
        
        # Register rules with router
        for pattern, rule in self.routing_rules.items():
            await self.router.add_route(pattern, rule)
    
    async def setup_backend_services(self):
        """Setup mock backend services for routing tests."""
        services_config = {
            "user_service": [
                ServiceEndpoint("localhost", 8001, 1, "healthy"),
                ServiceEndpoint("localhost", 8002, 1, "healthy"),
                ServiceEndpoint("localhost", 8003, 1, "unhealthy")
            ],
            "thread_service": [
                ServiceEndpoint("localhost", 8011, 3, "healthy"),  # Higher weight
                ServiceEndpoint("localhost", 8012, 1, "healthy"),
                ServiceEndpoint("localhost", 8013, 2, "healthy")
            ],
            "agent_service_v1": [
                ServiceEndpoint("localhost", 8021, 1, "healthy")
            ],
            "agent_service_v2": [
                ServiceEndpoint("localhost", 8031, 1, "healthy"),
                ServiceEndpoint("localhost", 8032, 1, "healthy")
            ],
            "admin_service": [
                ServiceEndpoint("localhost", 8041, 1, "healthy")
            ]
        }
        
        # Start mock servers for each service
        for service_name, endpoints in services_config.items():
            self.service_endpoints[service_name] = endpoints
            
            for endpoint in endpoints:
                if endpoint.health_status == "healthy":
                    server = await self.start_mock_service(
                        service_name, endpoint.host, endpoint.port
                    )
                    self.test_servers[f"{service_name}_{endpoint.port}"] = server
        
        # Register services with discovery
        for service_name, endpoints in services_config.items():
            await self.service_discovery.register_service(service_name, endpoints)
    
    async def start_mock_service(self, service_name: str, host: str, port: int):
        """Start a mock backend service."""
        from aiohttp import web
        
        async def handle_request(request):
            """Handle requests to mock service."""
            processing_time = 0.05  # Simulate processing
            await asyncio.sleep(processing_time)
            
            # Record routing metrics
            self.record_routing_metric(
                service_name, request.path, request.method, 
                processing_time, "success"
            )
            
            return web.Response(
                status=200,
                headers={
                    "X-Service-Name": service_name,
                    "X-Service-Port": str(port),
                    "X-Processing-Time": str(processing_time)
                },
                json={
                    "service": service_name,
                    "port": port,
                    "path": request.path,
                    "method": request.method,
                    "timestamp": time.time()
                }
            )
        
        async def handle_health(request):
            """Handle health check requests."""
            return web.Response(
                status=200,
                json={"status": "healthy", "service": service_name}
            )
        
        app = web.Application()
        app.router.add_route('*', '/{path:.*}', handle_request)
        app.router.add_get('/health', handle_health)
        app.router.add_get('/v2/health', handle_health)
        app.router.add_get('/admin/health', handle_health)
        
        # Start server
        server = await asyncio.create_task(
            aiohttp.web.create_server(app, host, port)
        )
        
        logger.info(f"Mock service {service_name} started on {host}:{port}")
        return server
    
    def record_routing_metric(self, service_name: str, path: str, method: str, 
                            processing_time: float, status: str):
        """Record routing metrics."""
        metric = {
            "service_name": service_name,
            "path": path,
            "method": method,
            "processing_time": processing_time,
            "status": status,
            "timestamp": time.time()
        }
        self.routing_metrics.append(metric)
    
    async def make_routed_request(self, path: str, method: str = "GET", 
                                headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make request through API gateway routing."""
        start_time = time.time()
        
        try:
            # Find matching route
            route_match = await self.router.find_route(path)
            
            if not route_match:
                return {
                    "status_code": 404,
                    "error": "No route found",
                    "path": path,
                    "response_time": time.time() - start_time
                }
            
            route_rule = route_match["rule"]
            service_name = route_rule.service_name
            
            # Get service endpoint via load balancer
            endpoint = await self.load_balancer.get_endpoint(
                service_name, route_rule.load_balancing_strategy
            )
            
            if not endpoint:
                self.failed_routes.append({
                    "path": path,
                    "service_name": service_name,
                    "reason": "no_healthy_endpoints",
                    "timestamp": time.time()
                })
                
                return {
                    "status_code": 503,
                    "error": "Service unavailable",
                    "path": path,
                    "service_name": service_name,
                    "response_time": time.time() - start_time
                }
            
            # Make request to backend service
            url = f"http://{endpoint.host}:{endpoint.port}{path}"
            
            async with aiohttp.ClientSession() as session:
                request_method = getattr(session, method.lower())
                
                async with request_method(
                    url, 
                    headers=headers or {},
                    timeout=aiohttp.ClientTimeout(total=route_rule.timeout_seconds)
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "service_name": service_name,
                        "endpoint": f"{endpoint.host}:{endpoint.port}",
                        "route_pattern": route_rule.path_pattern,
                        "load_balancing_strategy": route_rule.load_balancing_strategy
                    }
                    
                    if response.status == 200:
                        result["body"] = await response.json()
                    else:
                        result["body"] = await response.text()
                    
                    return result
                    
        except asyncio.TimeoutError:
            self.failed_routes.append({
                "path": path,
                "service_name": service_name if 'service_name' in locals() else "unknown",
                "reason": "timeout",
                "timestamp": time.time()
            })
            
            return {
                "status_code": 504,
                "error": "Gateway timeout",
                "path": path,
                "response_time": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "status_code": 500,
                "error": str(e),
                "path": path,
                "response_time": time.time() - start_time
            }
    
    async def test_load_balancing_distribution(self, service_name: str, 
                                             request_count: int) -> Dict[str, Any]:
        """Test load balancing distribution across service endpoints."""
        if service_name not in self.service_endpoints:
            return {"error": f"Service {service_name} not found"}
        
        # Find a route that uses this service
        test_path = None
        for pattern, rule in self.routing_rules.items():
            if rule.service_name == service_name:
                # Convert pattern to test path
                if pattern == "/api/v1/users":
                    test_path = "/api/v1/users"
                elif pattern == "/api/v1/users/*":
                    test_path = "/api/v1/users/123"
                elif pattern == "/api/v1/threads/[0-9a-f-]+":
                    test_path = "/api/v1/threads/550e8400-e29b-41d4-a716-446655440000"
                elif pattern == "/api/v2/agents":
                    test_path = "/api/v2/agents"
                elif pattern == "/api/v1/agents":
                    test_path = "/api/v1/agents"
                elif pattern == "/api/admin/*":
                    test_path = "/api/admin/users"
                break
        
        if not test_path:
            return {"error": f"No test path found for service {service_name}"}
        
        # Make multiple requests and track distribution
        endpoint_counts = {}
        results = []
        
        for i in range(request_count):
            result = await self.make_routed_request(test_path)
            results.append(result)
            
            if result.get("endpoint"):
                endpoint = result["endpoint"]
                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        # Calculate distribution metrics
        total_successful = len([r for r in results if r["status_code"] == 200])
        
        distribution_analysis = {
            "service_name": service_name,
            "test_path": test_path,
            "total_requests": request_count,
            "successful_requests": total_successful,
            "endpoint_distribution": endpoint_counts,
            "results": results
        }
        
        # Check if distribution follows load balancing strategy
        rule = next(rule for rule in self.routing_rules.values() 
                   if rule.service_name == service_name)
        
        if rule.load_balancing_strategy == "round_robin":
            # Should distribute evenly across healthy endpoints
            healthy_endpoints = [ep for ep in self.service_endpoints[service_name] 
                               if ep.health_status == "healthy"]
            expected_per_endpoint = total_successful // len(healthy_endpoints)
            
            distribution_analysis["expected_per_endpoint"] = expected_per_endpoint
            distribution_analysis["distribution_evenness"] = self.calculate_distribution_evenness(
                endpoint_counts, expected_per_endpoint
            )
        
        elif rule.load_balancing_strategy == "weighted":
            # Should distribute according to weights
            distribution_analysis["weight_compliance"] = self.check_weighted_distribution(
                service_name, endpoint_counts, total_successful
            )
        
        return distribution_analysis
    
    def calculate_distribution_evenness(self, endpoint_counts: Dict[str, int], 
                                      expected: int) -> float:
        """Calculate how evenly requests were distributed."""
        if not endpoint_counts:
            return 0.0
        
        # Calculate variance from expected distribution
        variance = sum((count - expected) ** 2 for count in endpoint_counts.values())
        variance /= len(endpoint_counts)
        
        # Return evenness score (lower variance = more even)
        max_possible_variance = expected ** 2
        evenness = max(0, 1 - (variance / max_possible_variance))
        
        return evenness
    
    def check_weighted_distribution(self, service_name: str, 
                                  endpoint_counts: Dict[str, int], 
                                  total_requests: int) -> Dict[str, Any]:
        """Check if distribution follows weight configuration."""
        endpoints = self.service_endpoints[service_name]
        total_weight = sum(ep.weight for ep in endpoints if ep.health_status == "healthy")
        
        weight_compliance = {}
        
        for endpoint in endpoints:
            if endpoint.health_status != "healthy":
                continue
                
            endpoint_key = f"{endpoint.host}:{endpoint.port}"
            actual_count = endpoint_counts.get(endpoint_key, 0)
            expected_ratio = endpoint.weight / total_weight
            expected_count = int(total_requests * expected_ratio)
            
            weight_compliance[endpoint_key] = {
                "weight": endpoint.weight,
                "expected_count": expected_count,
                "actual_count": actual_count,
                "ratio_compliance": actual_count / expected_count if expected_count > 0 else 0
            }
        
        return weight_compliance
    
    async def get_routing_metrics(self) -> Dict[str, Any]:
        """Get comprehensive routing metrics."""
        total_metrics = len(self.routing_metrics)
        total_failures = len(self.failed_routes)
        
        if total_metrics == 0:
            return {"total_requests": 0, "failures": 0}
        
        # Service breakdown
        service_breakdown = {}
        for metric in self.routing_metrics:
            service = metric["service_name"]
            if service not in service_breakdown:
                service_breakdown[service] = {
                    "requests": 0,
                    "total_processing_time": 0,
                    "avg_processing_time": 0
                }
            
            service_breakdown[service]["requests"] += 1
            service_breakdown[service]["total_processing_time"] += metric["processing_time"]
        
        # Calculate averages
        for service_data in service_breakdown.values():
            if service_data["requests"] > 0:
                service_data["avg_processing_time"] = (
                    service_data["total_processing_time"] / service_data["requests"]
                )
        
        # Route pattern breakdown
        route_patterns = list(self.routing_rules.keys())
        
        return {
            "total_requests": total_metrics,
            "total_failures": total_failures,
            "success_rate": (total_metrics / (total_metrics + total_failures)) * 100 if (total_metrics + total_failures) > 0 else 0,
            "service_breakdown": service_breakdown,
            "configured_routes": len(self.routing_rules),
            "route_patterns": route_patterns,
            "failure_breakdown": self.analyze_failures()
        }
    
    def analyze_failures(self) -> Dict[str, Any]:
        """Analyze routing failures by type."""
        failure_types = {}
        
        for failure in self.failed_routes:
            reason = failure["reason"]
            failure_types[reason] = failure_types.get(reason, 0) + 1
        
        return failure_types
    
    async def cleanup(self):
        """Clean up routing resources."""
        try:
            # Stop all mock servers
            for server in self.test_servers.values():
                server.close()
                await server.wait_closed()
            
            if self.router:
                await self.router.shutdown()
            
            if self.route_manager:
                await self.route_manager.shutdown()
            
            if self.load_balancer:
                await self.load_balancer.shutdown()
            
            if self.service_discovery:
                await self.service_discovery.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def api_routing_manager():
    """Create API routing manager for L3 testing."""
    manager = ApiRoutingManager()
    await manager.initialize_routing()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_exact_path_routing(api_routing_manager):
    """Test exact path routing to correct services."""
    test_cases = [
        ("/api/v1/users", "user_service"),
        ("/api/v2/agents", "agent_service_v2"),
        ("/api/v1/agents", "agent_service_v1"),
    ]
    
    for path, expected_service in test_cases:
        result = await api_routing_manager.make_routed_request(path)
        
        assert result["status_code"] == 200
        assert result["service_name"] == expected_service
        assert "endpoint" in result
        assert result["response_time"] < 1.0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_wildcard_path_routing(api_routing_manager):
    """Test wildcard and regex pattern routing."""
    test_cases = [
        ("/api/v1/users/123", "user_service"),
        ("/api/v1/users/abc/profile", "user_service"),
        ("/api/v1/threads/550e8400-e29b-41d4-a716-446655440000", "thread_service"),
        ("/api/admin/users", "admin_service"),
        ("/api/admin/settings/config", "admin_service"),
    ]
    
    for path, expected_service in test_cases:
        result = await api_routing_manager.make_routed_request(path)
        
        assert result["status_code"] == 200
        assert result["service_name"] == expected_service
        assert result["route_pattern"] in [
            "/api/v1/users/*", 
            r"/api/v1/threads/[0-9a-f-]+", 
            "/api/admin/*"
        ]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_version_based_routing(api_routing_manager):
    """Test API version-based routing."""
    # Test v1 agent endpoint
    v1_result = await api_routing_manager.make_routed_request("/api/v1/agents")
    assert v1_result["status_code"] == 200
    assert v1_result["service_name"] == "agent_service_v1"
    
    # Test v2 agent endpoint
    v2_result = await api_routing_manager.make_routed_request("/api/v2/agents")
    assert v2_result["status_code"] == 200
    assert v2_result["service_name"] == "agent_service_v2"
    
    # Different services should be used
    assert v1_result["service_name"] != v2_result["service_name"]
    assert v1_result["endpoint"] != v2_result["endpoint"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_load_balancing_strategies(api_routing_manager):
    """Test different load balancing strategies."""
    # Test round-robin distribution (user service)
    user_distribution = await api_routing_manager.test_load_balancing_distribution(
        "user_service", 20
    )
    
    assert user_distribution["successful_requests"] >= 18  # Most should succeed
    assert len(user_distribution["endpoint_distribution"]) >= 2  # Multiple endpoints used
    assert user_distribution["distribution_evenness"] > 0.7  # Should be fairly even
    
    # Test weighted distribution (thread service)
    thread_distribution = await api_routing_manager.test_load_balancing_distribution(
        "thread_service", 30
    )
    
    assert thread_distribution["successful_requests"] >= 28
    
    # Check that weighted distribution respects weights
    weight_compliance = thread_distribution["weight_compliance"]
    for endpoint_data in weight_compliance.values():
        # Allow some variance in weight compliance
        assert endpoint_data["ratio_compliance"] > 0.5
        assert endpoint_data["ratio_compliance"] < 2.0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_routing_priority_handling(api_routing_manager):
    """Test routing priority when multiple patterns could match."""
    # Admin routes should have higher priority than wildcard routes
    admin_result = await api_routing_manager.make_routed_request("/api/admin/users")
    
    assert admin_result["status_code"] == 200
    assert admin_result["service_name"] == "admin_service"
    assert admin_result["route_pattern"] == "/api/admin/*"
    
    # Specific user route should match before wildcard
    user_result = await api_routing_manager.make_routed_request("/api/v1/users")
    
    assert user_result["status_code"] == 200
    assert user_result["service_name"] == "user_service"
    assert user_result["route_pattern"] == "/api/v1/users"  # Exact match, not wildcard


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_routing_requests(api_routing_manager):
    """Test concurrent requests across different routes."""
    # Create concurrent requests to different services
    concurrent_requests = [
        api_routing_manager.make_routed_request("/api/v1/users"),
        api_routing_manager.make_routed_request("/api/v1/users/123"),
        api_routing_manager.make_routed_request("/api/v2/agents"),
        api_routing_manager.make_routed_request("/api/v1/threads/550e8400-e29b-41d4-a716-446655440000"),
        api_routing_manager.make_routed_request("/api/admin/settings"),
    ] * 5  # 25 total concurrent requests
    
    start_time = time.time()
    results = await asyncio.gather(*concurrent_requests)
    execution_time = time.time() - start_time
    
    # Analyze results
    successful = [r for r in results if r["status_code"] == 200]
    
    assert len(successful) >= 23  # Most should succeed
    assert execution_time < 5.0  # Should complete quickly
    
    # Check that different services were used
    services_used = set(r["service_name"] for r in successful)
    assert len(services_used) >= 4  # Multiple services should be hit


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_route_not_found_handling(api_routing_manager):
    """Test handling of requests to non-existent routes."""
    non_existent_paths = [
        "/api/v3/unknown",
        "/completely/invalid/path",
        "/api/v1/nonexistent",
        "/admin/no-api-prefix"
    ]
    
    for path in non_existent_paths:
        result = await api_routing_manager.make_routed_request(path)
        
        assert result["status_code"] == 404
        assert "No route found" in result["error"]
        assert result["path"] == path


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_service_health_check_integration(api_routing_manager):
    """Test integration with service health checks."""
    # Test that healthy services receive requests
    healthy_result = await api_routing_manager.make_routed_request("/api/v2/agents")
    assert healthy_result["status_code"] == 200
    
    # Simulate service going unhealthy
    service_name = "agent_service_v2"
    for endpoint in api_routing_manager.service_endpoints[service_name]:
        endpoint.health_status = "unhealthy"
    
    # Update service discovery
    await api_routing_manager.service_discovery.update_service_health(
        service_name, "unhealthy"
    )
    
    # Requests should now fail with 503
    unhealthy_result = await api_routing_manager.make_routed_request("/api/v2/agents")
    assert unhealthy_result["status_code"] == 503
    assert "Service unavailable" in unhealthy_result["error"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_routing_performance_requirements(api_routing_manager):
    """Test routing performance meets requirements."""
    # Test response time for route resolution
    response_times = []
    
    for i in range(50):
        result = await api_routing_manager.make_routed_request("/api/v1/users")
        if result["status_code"] == 200:
            response_times.append(result["response_time"])
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    
    # Routing should add minimal overhead
    assert avg_response_time < 0.3  # Average < 300ms
    assert max_response_time < 1.0  # Max < 1 second
    
    # Test concurrent routing performance
    concurrent_tasks = []
    for i in range(20):
        task = api_routing_manager.make_routed_request(f"/api/v1/users/{i}")
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # Should handle concurrent routing efficiently
    assert concurrent_duration < 2.0  # 20 requests in < 2 seconds
    
    successful_concurrent = [r for r in concurrent_results if r["status_code"] == 200]
    assert len(successful_concurrent) >= 18  # Most should succeed


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_routing_metrics_accuracy(api_routing_manager):
    """Test accuracy of routing metrics collection."""
    # Generate test traffic
    test_requests = [
        "/api/v1/users",
        "/api/v1/users/123",
        "/api/v2/agents",
        "/api/v1/threads/550e8400-e29b-41d4-a716-446655440000",
        "/api/admin/config"
    ]
    
    for path in test_requests * 3:  # 15 total requests
        await api_routing_manager.make_routed_request(path)
    
    # Get routing metrics
    metrics = await api_routing_manager.get_routing_metrics()
    
    # Verify metrics accuracy
    assert metrics["total_requests"] == 15
    assert metrics["configured_routes"] == 6
    assert metrics["success_rate"] >= 80
    
    # Verify service breakdown
    service_breakdown = metrics["service_breakdown"]
    assert "user_service" in service_breakdown
    assert "agent_service_v2" in service_breakdown
    assert "thread_service" in service_breakdown
    assert "admin_service" in service_breakdown
    
    # Verify all services have reasonable processing times
    for service_data in service_breakdown.values():
        assert service_data["avg_processing_time"] > 0
        assert service_data["avg_processing_time"] < 0.5  # Should be fast