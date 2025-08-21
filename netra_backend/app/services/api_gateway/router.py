"""API Gateway Router implementation."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Route:
    """Represents an API route configuration."""
    path: str
    method: str
    target: str
    weight: int = 100
    enabled: bool = True


class LoadBalancer:
    """Load balancer for distributing requests across targets."""
    
    def __init__(self):
        self.targets: List[str] = []
        self.weights: Dict[str, int] = {}
    
    def add_target(self, target: str, weight: int = 100) -> None:
        """Add a target with optional weight."""
        if target not in self.targets:
            self.targets.append(target)
        self.weights[target] = weight
    
    def get_target(self) -> Optional[str]:
        """Get next target based on load balancing strategy."""
        if not self.targets:
            return None
        # Simple round-robin for now
        return self.targets[0]


class RouteManager:
    """Manages API routes and routing rules."""
    
    def __init__(self):
        self.routes: List[Route] = []
        self.route_map: Dict[str, Route] = {}
    
    def add_route(self, route: Route) -> None:
        """Add a new route."""
        route_key = f"{route.method}:{route.path}"
        self.routes.append(route)
        self.route_map[route_key] = route
    
    def find_route(self, path: str, method: str) -> Optional[Route]:
        """Find matching route for path and method."""
        route_key = f"{method}:{path}"
        return self.route_map.get(route_key)
    
    def get_routes(self) -> List[Route]:
        """Get all routes."""
        return self.routes.copy()


class ApiGatewayRouter:
    """Main API Gateway Router class."""
    
    def __init__(self):
        self.route_manager = RouteManager()
        self.load_balancer = LoadBalancer()
        self.enabled = True
    
    def add_route(self, path: str, method: str, target: str, weight: int = 100) -> None:
        """Add a new route configuration."""
        route = Route(path=path, method=method, target=target, weight=weight)
        self.route_manager.add_route(route)
        self.load_balancer.add_target(target, weight)
    
    def route_request(self, path: str, method: str) -> Optional[str]:
        """Route a request to the appropriate target."""
        if not self.enabled:
            return None
            
        route = self.route_manager.find_route(path, method)
        if not route or not route.enabled:
            return None
            
        return route.target
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get router health status."""
        return {
            'enabled': self.enabled,
            'routes_count': len(self.route_manager.routes),
            'targets_count': len(self.load_balancer.targets)
        }
    
    def disable(self) -> None:
        """Disable the router."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable the router."""
        self.enabled = True
