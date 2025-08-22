"""Route Manager for API Gateway

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (API routing and traffic management)
- Business Goal: Intelligent request routing and load distribution
- Value Impact: Optimizes API performance and enables advanced routing strategies
- Strategic Impact: Enables sophisticated API traffic management for enterprise clients

Manages request routing, load balancing, and traffic distribution.
"""

import asyncio
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RoutingStrategy(Enum):
    """Available routing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    HASH_BASED = "hash_based"
    LATENCY_BASED = "latency_based"


@dataclass
class RouteTarget:
    """Represents a route target/backend."""
    target_id: str
    url: str
    weight: int = 1
    max_connections: int = 100
    current_connections: int = 0
    is_healthy: bool = True
    average_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def load_factor(self) -> float:
        """Calculate current load factor (0.0 to 1.0)."""
        if self.max_connections == 0:
            return 0.0
        return self.current_connections / self.max_connections


@dataclass
class RouteRule:
    """Represents a routing rule."""
    rule_id: str
    path_pattern: str
    method: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    targets: List[RouteTarget] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    priority: int = 100
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    target: RouteTarget
    rule: RouteRule
    decision_time_ms: float
    strategy_used: RoutingStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)


class RouteManager:
    """Manages API routing rules and target selection."""
    
    def __init__(self):
        """Initialize the route manager."""
        self._routes: Dict[str, RouteRule] = {}
        self._route_counters: Dict[str, int] = {}  # For round-robin
        self._health_monitors: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def add_route(self, route_rule: RouteRule) -> None:
        """Add a new routing rule."""
        async with self._lock:
            self._routes[route_rule.rule_id] = route_rule
            self._route_counters[route_rule.rule_id] = 0
            logger.info(f"Added route rule: {route_rule.rule_id} for pattern {route_rule.path_pattern}")
    
    async def remove_route(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        async with self._lock:
            if rule_id in self._routes:
                del self._routes[rule_id]
                self._route_counters.pop(rule_id, None)
                logger.info(f"Removed route rule: {rule_id}")
                return True
            return False
    
    async def find_route(self, path: str, method: str, headers: Dict[str, str], 
                        query_params: Dict[str, str]) -> Optional[RoutingDecision]:
        """Find the best route for a request."""
        start_time = datetime.now(timezone.utc)
        
        async with self._lock:
            # Find matching routes sorted by priority
            matching_routes = []
            for route in self._routes.values():
                if await self._matches_route(route, path, method, headers, query_params):
                    matching_routes.append(route)
            
            if not matching_routes:
                return None
            
            # Sort by priority (lower number = higher priority)
            matching_routes.sort(key=lambda r: r.priority)
            
            # Select the best route and target
            for route in matching_routes:
                if not route.is_active or not route.targets:
                    continue
                
                # Get healthy targets
                healthy_targets = [t for t in route.targets if t.is_healthy]
                if not healthy_targets:
                    continue
                
                # Select target based on strategy
                target = await self._select_target(route, healthy_targets)
                if target:
                    decision_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    return RoutingDecision(
                        target=target,
                        rule=route,
                        decision_time_ms=decision_time,
                        strategy_used=route.strategy
                    )
            
            return None
    
    async def add_target_to_route(self, rule_id: str, target: RouteTarget) -> bool:
        """Add a target to an existing route."""
        async with self._lock:
            if rule_id not in self._routes:
                return False
            
            route = self._routes[rule_id]
            route.targets.append(target)
            logger.info(f"Added target {target.target_id} to route {rule_id}")
            return True
    
    async def remove_target_from_route(self, rule_id: str, target_id: str) -> bool:
        """Remove a target from a route."""
        async with self._lock:
            if rule_id not in self._routes:
                return False
            
            route = self._routes[rule_id]
            route.targets = [t for t in route.targets if t.target_id != target_id]
            logger.info(f"Removed target {target_id} from route {rule_id}")
            return True
    
    async def update_target_health(self, target_id: str, is_healthy: bool, 
                                 latency_ms: Optional[float] = None) -> None:
        """Update health status of a target."""
        async with self._lock:
            for route in self._routes.values():
                for target in route.targets:
                    if target.target_id == target_id:
                        target.is_healthy = is_healthy
                        target.last_health_check = datetime.now(timezone.utc)
                        if latency_ms is not None:
                            # Simple moving average
                            if target.average_latency_ms == 0:
                                target.average_latency_ms = latency_ms
                            else:
                                target.average_latency_ms = (target.average_latency_ms * 0.9) + (latency_ms * 0.1)
                        break
    
    async def increment_target_connections(self, target_id: str) -> None:
        """Increment connection count for a target."""
        async with self._lock:
            for route in self._routes.values():
                for target in route.targets:
                    if target.target_id == target_id:
                        target.current_connections += 1
                        return
    
    async def decrement_target_connections(self, target_id: str) -> None:
        """Decrement connection count for a target."""
        async with self._lock:
            for route in self._routes.values():
                for target in route.targets:
                    if target.target_id == target_id:
                        target.current_connections = max(0, target.current_connections - 1)
                        return
    
    async def get_route_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        async with self._lock:
            stats = {
                "total_routes": len(self._routes),
                "active_routes": len([r for r in self._routes.values() if r.is_active]),
                "total_targets": sum(len(r.targets) for r in self._routes.values()),
                "healthy_targets": sum(len([t for t in r.targets if t.is_healthy]) for r in self._routes.values()),
                "routes": []
            }
            
            for route in self._routes.values():
                route_stats = {
                    "rule_id": route.rule_id,
                    "path_pattern": route.path_pattern,
                    "strategy": route.strategy.value,
                    "priority": route.priority,
                    "is_active": route.is_active,
                    "target_count": len(route.targets),
                    "healthy_target_count": len([t for t in route.targets if t.is_healthy]),
                    "targets": [
                        {
                            "target_id": t.target_id,
                            "url": t.url,
                            "weight": t.weight,
                            "is_healthy": t.is_healthy,
                            "current_connections": t.current_connections,
                            "load_factor": t.load_factor,
                            "average_latency_ms": t.average_latency_ms
                        }
                        for t in route.targets
                    ]
                }
                stats["routes"].append(route_stats)
            
            return stats
    
    async def _matches_route(self, route: RouteRule, path: str, method: str, 
                           headers: Dict[str, str], query_params: Dict[str, str]) -> bool:
        """Check if a request matches a route rule."""
        # Simple pattern matching (would be more sophisticated in production)
        if route.path_pattern != "*" and not path.startswith(route.path_pattern.rstrip("*")):
            return False
        
        if route.method and route.method != method:
            return False
        
        # Check required headers
        for header_key, header_value in route.headers.items():
            if headers.get(header_key) != header_value:
                return False
        
        # Check required query parameters
        for param_key, param_value in route.query_params.items():
            if query_params.get(param_key) != param_value:
                return False
        
        return True
    
    async def _select_target(self, route: RouteRule, healthy_targets: List[RouteTarget]) -> Optional[RouteTarget]:
        """Select a target based on the routing strategy."""
        if not healthy_targets:
            return None
        
        if route.strategy == RoutingStrategy.ROUND_ROBIN:
            return await self._round_robin_selection(route, healthy_targets)
        
        elif route.strategy == RoutingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_selection(healthy_targets)
        
        elif route.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_selection(healthy_targets)
        
        elif route.strategy == RoutingStrategy.RANDOM:
            return random.choice(healthy_targets)
        
        elif route.strategy == RoutingStrategy.LATENCY_BASED:
            return await self._latency_based_selection(healthy_targets)
        
        else:
            # Default to round robin
            return await self._round_robin_selection(route, healthy_targets)
    
    async def _round_robin_selection(self, route: RouteRule, targets: List[RouteTarget]) -> RouteTarget:
        """Round-robin target selection."""
        counter = self._route_counters.get(route.rule_id, 0)
        selected = targets[counter % len(targets)]
        self._route_counters[route.rule_id] = counter + 1
        return selected
    
    async def _weighted_round_robin_selection(self, targets: List[RouteTarget]) -> RouteTarget:
        """Weighted round-robin target selection."""
        total_weight = sum(t.weight for t in targets)
        if total_weight == 0:
            return random.choice(targets)
        
        random_weight = random.randint(1, total_weight)
        current_weight = 0
        
        for target in targets:
            current_weight += target.weight
            if random_weight <= current_weight:
                return target
        
        return targets[-1]  # Fallback
    
    async def _least_connections_selection(self, targets: List[RouteTarget]) -> RouteTarget:
        """Least connections target selection."""
        return min(targets, key=lambda t: t.current_connections)
    
    async def _latency_based_selection(self, targets: List[RouteTarget]) -> RouteTarget:
        """Latency-based target selection."""
        # Filter out targets with no latency data, then select lowest latency
        targets_with_latency = [t for t in targets if t.average_latency_ms > 0]
        if targets_with_latency:
            return min(targets_with_latency, key=lambda t: t.average_latency_ms)
        return random.choice(targets)
    
    async def enable_route(self, rule_id: str) -> bool:
        """Enable a route rule."""
        async with self._lock:
            if rule_id in self._routes:
                self._routes[rule_id].is_active = True
                logger.info(f"Enabled route: {rule_id}")
                return True
            return False
    
    async def disable_route(self, rule_id: str) -> bool:
        """Disable a route rule."""
        async with self._lock:
            if rule_id in self._routes:
                self._routes[rule_id].is_active = False
                logger.info(f"Disabled route: {rule_id}")
                return True
            return False
    
    async def cleanup_unhealthy_targets(self, max_unhealthy_duration_minutes: int = 30) -> int:
        """Remove targets that have been unhealthy for too long."""
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            removed_count = 0
            
            for route in self._routes.values():
                targets_to_remove = []
                for target in route.targets:
                    if (not target.is_healthy and 
                        target.last_health_check and
                        (current_time - target.last_health_check).total_seconds() > max_unhealthy_duration_minutes * 60):
                        targets_to_remove.append(target.target_id)
                
                for target_id in targets_to_remove:
                    route.targets = [t for t in route.targets if t.target_id != target_id]
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} unhealthy targets")
            return removed_count


# Global route manager instance
route_manager = RouteManager()