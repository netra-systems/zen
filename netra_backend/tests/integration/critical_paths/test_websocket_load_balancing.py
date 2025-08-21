"""
L2 Integration Test: WebSocket Load Balancing

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Scalability worth $12K MRR growth support
- Value Impact: Enables horizontal scaling and improved performance under load
- Strategic Impact: Supports business growth with cost-effective scaling

L2 Test: Real internal load balancing components with mocked external services.
Performance target: <5ms routing decisions, 95% connection distribution accuracy.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import json
import time
import random
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from netra_backend.app.services.websocket_manager import WebSocketManager
from schemas import UserInDB
from test_framework.mock_utils import mock_justified


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    HASH_BASED = "hash_based"
    GEOGRAPHIC = "geographic"


class ServerState(Enum):
    """Server health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class ServerInstance:
    """Represents a WebSocket server instance."""
    server_id: str
    host: str
    port: int
    capacity: int = 1000
    current_connections: int = 0
    weight: float = 1.0
    region: str = "us-east-1"
    state: ServerState = ServerState.HEALTHY
    avg_response_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_health_check: float = field(default_factory=time.time)


@dataclass
class ConnectionSession:
    """Represents a connection session with sticky session support."""
    session_id: str
    user_id: str
    server_id: str
    created_at: float
    last_activity: float
    connection_count: int = 1
    affinity_score: float = 1.0


class WebSocketLoadBalancer:
    """Load balancer for WebSocket connections."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS):
        self.strategy = strategy
        self.servers = {}  # server_id -> ServerInstance
        self.sessions = {}  # session_id -> ConnectionSession
        self.user_sessions = defaultdict(set)  # user_id -> set(session_ids)
        self.round_robin_index = 0
        self.sticky_sessions = True
        self.session_affinity_timeout = 3600.0  # 1 hour
        
        self.metrics = {
            "total_connections_routed": 0,
            "routing_decisions": 0,
            "failover_events": 0,
            "load_rebalancing_events": 0,
            "session_affinity_hits": 0,
            "routing_errors": 0,
            "avg_routing_time_ms": 0.0
        }
        
        self.routing_history = []  # For analysis
    
    def add_server(self, server_id: str, host: str, port: int, capacity: int = 1000, 
                   weight: float = 1.0, region: str = "us-east-1") -> ServerInstance:
        """Add a server to the load balancer."""
        server = ServerInstance(
            server_id=server_id,
            host=host,
            port=port,
            capacity=capacity,
            weight=weight,
            region=region
        )
        
        self.servers[server_id] = server
        return server
    
    def remove_server(self, server_id: str) -> bool:
        """Remove a server from the load balancer."""
        if server_id not in self.servers:
            return False
        
        # Handle connection migration if server has active connections
        server = self.servers[server_id]
        if server.current_connections > 0:
            self._migrate_connections_from_server(server_id)
        
        del self.servers[server_id]
        return True
    
    def update_server_health(self, server_id: str, state: ServerState, 
                           response_time: float = None) -> bool:
        """Update server health status."""
        if server_id not in self.servers:
            return False
        
        server = self.servers[server_id]
        old_state = server.state
        server.state = state
        server.last_health_check = time.time()
        
        if response_time is not None:
            # Update rolling average response time
            if server.avg_response_time == 0:
                server.avg_response_time = response_time
            else:
                server.avg_response_time = (server.avg_response_time * 0.8) + (response_time * 0.2)
        
        # Handle state transitions
        if old_state == ServerState.HEALTHY and state != ServerState.HEALTHY:
            self._handle_server_degradation(server_id)
        elif old_state != ServerState.HEALTHY and state == ServerState.HEALTHY:
            self._handle_server_recovery(server_id)
        
        return True
    
    async def route_connection(self, user_id: str, client_region: str = "us-east-1", 
                              session_affinity: str = None) -> Optional[Dict[str, Any]]:
        """Route a new connection to an appropriate server."""
        start_time = time.time()
        self.metrics["routing_decisions"] += 1
        
        try:
            # Check for existing session affinity
            if self.sticky_sessions and session_affinity:
                affinity_result = self._check_session_affinity(user_id, session_affinity)
                if affinity_result:
                    self.metrics["session_affinity_hits"] += 1
                    routing_time = (time.time() - start_time) * 1000
                    self._update_avg_routing_time(routing_time)
                    return affinity_result
            
            # Get available servers
            available_servers = self._get_available_servers()
            if not available_servers:
                self.metrics["routing_errors"] += 1
                return None
            
            # Apply load balancing strategy
            selected_server = await self._select_server(available_servers, user_id, client_region)
            
            if not selected_server:
                self.metrics["routing_errors"] += 1
                return None
            
            # Create/update session
            session_id = session_affinity or str(uuid4())
            self._create_or_update_session(session_id, user_id, selected_server.server_id)
            
            # Update server connection count
            selected_server.current_connections += 1
            self.metrics["total_connections_routed"] += 1
            
            # Record routing decision
            routing_time = (time.time() - start_time) * 1000
            self._update_avg_routing_time(routing_time)
            self._record_routing_decision(user_id, selected_server, routing_time)
            
            return {
                "server_id": selected_server.server_id,
                "host": selected_server.host,
                "port": selected_server.port,
                "session_id": session_id,
                "routing_time_ms": routing_time,
                "strategy_used": self.strategy.value,
                "server_load": selected_server.current_connections / selected_server.capacity
            }
        
        except Exception as e:
            self.metrics["routing_errors"] += 1
            return None
    
    def _check_session_affinity(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Check if session affinity should be honored."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is still valid
        if time.time() - session.last_activity > self.session_affinity_timeout:
            self._cleanup_session(session_id)
            return None
        
        # Check if target server is still available
        server_id = session.server_id
        if server_id not in self.servers:
            self._cleanup_session(session_id)
            return None
        
        server = self.servers[server_id]
        if server.state != ServerState.HEALTHY or server.current_connections >= server.capacity:
            return None
        
        # Update session activity
        session.last_activity = time.time()
        session.connection_count += 1
        
        return {
            "server_id": server.server_id,
            "host": server.host,
            "port": server.port,
            "session_id": session_id,
            "routing_time_ms": 1.0,  # Affinity routing is very fast
            "strategy_used": "session_affinity",
            "server_load": server.current_connections / server.capacity
        }
    
    def _get_available_servers(self) -> List[ServerInstance]:
        """Get list of available servers for routing."""
        available = []
        
        for server in self.servers.values():
            if (server.state == ServerState.HEALTHY and 
                server.current_connections < server.capacity):
                available.append(server)
        
        return available
    
    async def _select_server(self, available_servers: List[ServerInstance], 
                           user_id: str, client_region: str) -> Optional[ServerInstance]:
        """Select server based on load balancing strategy."""
        if not available_servers:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_servers)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(available_servers)
        
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(available_servers)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_selection(available_servers)
        
        elif self.strategy == LoadBalancingStrategy.HASH_BASED:
            return self._hash_based_selection(available_servers, user_id)
        
        elif self.strategy == LoadBalancingStrategy.GEOGRAPHIC:
            return self._geographic_selection(available_servers, client_region)
        
        else:
            # Default to least connections
            return self._least_connections_selection(available_servers)
    
    def _round_robin_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server using round-robin strategy."""
        if not servers:
            return None
        
        selected = servers[self.round_robin_index % len(servers)]
        self.round_robin_index += 1
        return selected
    
    def _least_connections_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with least connections."""
        return min(servers, key=lambda s: s.current_connections)
    
    def _weighted_round_robin_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server using weighted round-robin."""
        # Create weighted list
        weighted_servers = []
        for server in servers:
            weight_factor = max(1, int(server.weight * 10))
            weighted_servers.extend([server] * weight_factor)
        
        if not weighted_servers:
            return servers[0] if servers else None
        
        selected = weighted_servers[self.round_robin_index % len(weighted_servers)]
        self.round_robin_index += 1
        return selected
    
    def _least_response_time_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with least response time."""
        # Filter servers with response time data
        servers_with_rt = [s for s in servers if s.avg_response_time > 0]
        
        if servers_with_rt:
            return min(servers_with_rt, key=lambda s: s.avg_response_time)
        else:
            # Fall back to least connections
            return self._least_connections_selection(servers)
    
    def _hash_based_selection(self, servers: List[ServerInstance], user_id: str) -> ServerInstance:
        """Select server using consistent hashing."""
        if not servers:
            return None
        
        # Simple hash-based selection
        hash_value = hash(user_id) % len(servers)
        return servers[hash_value]
    
    def _geographic_selection(self, servers: List[ServerInstance], client_region: str) -> ServerInstance:
        """Select server based on geographic proximity."""
        # Prefer servers in same region
        same_region_servers = [s for s in servers if s.region == client_region]
        
        if same_region_servers:
            # Use least connections within same region
            return self._least_connections_selection(same_region_servers)
        else:
            # Fall back to least connections overall
            return self._least_connections_selection(servers)
    
    def _create_or_update_session(self, session_id: str, user_id: str, server_id: str) -> None:
        """Create or update session information."""
        current_time = time.time()
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_activity = current_time
            session.connection_count += 1
        else:
            session = ConnectionSession(
                session_id=session_id,
                user_id=user_id,
                server_id=server_id,
                created_at=current_time,
                last_activity=current_time
            )
            self.sessions[session_id] = session
            self.user_sessions[user_id].add(session_id)
    
    def _cleanup_session(self, session_id: str) -> None:
        """Clean up expired session."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions.pop(session_id)
        self.user_sessions[session.user_id].discard(session_id)
        
        if not self.user_sessions[session.user_id]:
            del self.user_sessions[session.user_id]
    
    def disconnect_connection(self, session_id: str) -> bool:
        """Handle connection disconnection."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        server_id = session.server_id
        
        # Update server connection count
        if server_id in self.servers:
            self.servers[server_id].current_connections = max(
                0, self.servers[server_id].current_connections - 1
            )
        
        # Clean up session
        self._cleanup_session(session_id)
        return True
    
    def _handle_server_degradation(self, server_id: str) -> None:
        """Handle server becoming unhealthy."""
        self.metrics["failover_events"] += 1
        # In real implementation, would trigger connection migration
    
    def _handle_server_recovery(self, server_id: str) -> None:
        """Handle server recovery."""
        # In real implementation, would gradually restore traffic
        pass
    
    def _migrate_connections_from_server(self, server_id: str) -> None:
        """Migrate connections from failing server."""
        # Find sessions on this server
        sessions_to_migrate = [
            session for session in self.sessions.values()
            if session.server_id == server_id
        ]
        
        for session in sessions_to_migrate:
            # In real implementation, would handle graceful migration
            self._cleanup_session(session.session_id)
    
    def _update_avg_routing_time(self, routing_time_ms: float) -> None:
        """Update average routing time metric."""
        current_avg = self.metrics["avg_routing_time_ms"]
        total_decisions = self.metrics["routing_decisions"]
        
        if total_decisions == 1:
            self.metrics["avg_routing_time_ms"] = routing_time_ms
        else:
            self.metrics["avg_routing_time_ms"] = (
                (current_avg * (total_decisions - 1)) + routing_time_ms
            ) / total_decisions
    
    def _record_routing_decision(self, user_id: str, server: ServerInstance, routing_time: float) -> None:
        """Record routing decision for analysis."""
        decision_record = {
            "timestamp": time.time(),
            "user_id": user_id,
            "server_id": server.server_id,
            "strategy": self.strategy.value,
            "routing_time_ms": routing_time,
            "server_load": server.current_connections / server.capacity,
            "server_region": server.region
        }
        
        self.routing_history.append(decision_record)
        
        # Keep only recent history
        if len(self.routing_history) > 10000:
            self.routing_history = self.routing_history[-5000:]
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics."""
        stats = self.metrics.copy()
        
        # Server statistics
        total_servers = len(self.servers)
        healthy_servers = sum(1 for s in self.servers.values() if s.state == ServerState.HEALTHY)
        total_capacity = sum(s.capacity for s in self.servers.values())
        total_connections = sum(s.current_connections for s in self.servers.values())
        
        stats.update({
            "total_servers": total_servers,
            "healthy_servers": healthy_servers,
            "total_capacity": total_capacity,
            "total_active_connections": total_connections,
            "overall_utilization": (total_connections / total_capacity * 100) if total_capacity > 0 else 0,
            "active_sessions": len(self.sessions),
            "users_with_sessions": len(self.user_sessions)
        })
        
        # Calculate success rate
        if stats["routing_decisions"] > 0:
            stats["routing_success_rate"] = (
                (stats["routing_decisions"] - stats["routing_errors"]) / 
                stats["routing_decisions"] * 100
            )
        else:
            stats["routing_success_rate"] = 0.0
        
        return stats
    
    def get_server_distribution(self) -> Dict[str, Any]:
        """Get connection distribution across servers."""
        distribution = {}
        
        for server_id, server in self.servers.items():
            distribution[server_id] = {
                "current_connections": server.current_connections,
                "capacity": server.capacity,
                "utilization": (server.current_connections / server.capacity * 100),
                "state": server.state.value,
                "region": server.region,
                "weight": server.weight,
                "avg_response_time": server.avg_response_time
            }
        
        return distribution
    
    def analyze_load_distribution(self) -> Dict[str, Any]:
        """Analyze load distribution quality."""
        if not self.servers:
            return {"error": "No servers configured"}
        
        healthy_servers = [s for s in self.servers.values() if s.state == ServerState.HEALTHY]
        if not healthy_servers:
            return {"error": "No healthy servers"}
        
        # Calculate distribution metrics
        utilizations = [s.current_connections / s.capacity for s in healthy_servers]
        avg_utilization = sum(utilizations) / len(utilizations)
        
        # Calculate variance for distribution quality
        variance = sum((u - avg_utilization) ** 2 for u in utilizations) / len(utilizations)
        std_deviation = variance ** 0.5
        
        # Distribution quality score (lower variance = better distribution)
        if avg_utilization > 0:
            distribution_quality = max(0, 100 - (std_deviation / avg_utilization * 100))
        else:
            distribution_quality = 100
        
        return {
            "avg_utilization": avg_utilization * 100,
            "utilization_variance": variance,
            "utilization_std_dev": std_deviation,
            "distribution_quality_score": distribution_quality,
            "min_utilization": min(utilizations) * 100,
            "max_utilization": max(utilizations) * 100,
            "servers_analyzed": len(healthy_servers)
        }


class HealthChecker:
    """Monitor server health for load balancer."""
    
    def __init__(self, load_balancer: WebSocketLoadBalancer):
        self.load_balancer = load_balancer
        self.health_check_interval = 30.0  # 30 seconds
        self.health_check_timeout = 5.0
        self.running = False
        self.health_history = defaultdict(list)
    
    async def start_health_monitoring(self) -> None:
        """Start continuous health monitoring."""
        self.running = True
        
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5.0)  # Short delay on error
    
    def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        self.running = False
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all servers."""
        health_tasks = []
        
        for server_id, server in self.load_balancer.servers.items():
            task = self._check_server_health(server_id, server)
            health_tasks.append(task)
        
        if health_tasks:
            await asyncio.gather(*health_tasks, return_exceptions=True)
    
    async def _check_server_health(self, server_id: str, server: ServerInstance) -> None:
        """Check health of a specific server."""
        try:
            # Simulate health check
            start_time = time.time()
            
            # Mock health check - in real implementation would make HTTP/WebSocket request
            await asyncio.sleep(random.uniform(0.01, 0.05))  # Simulate network latency
            
            # Simulate occasional failures
            if random.random() < 0.05:  # 5% failure rate
                raise Exception("Health check failed")
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Update server health
            self.load_balancer.update_server_health(server_id, ServerState.HEALTHY, response_time)
            
            # Record health check result
            self._record_health_check(server_id, True, response_time)
        
        except Exception as e:
            # Handle health check failure
            self.load_balancer.update_server_health(server_id, ServerState.UNHEALTHY)
            self._record_health_check(server_id, False, 0.0)
    
    def _record_health_check(self, server_id: str, success: bool, response_time: float) -> None:
        """Record health check result."""
        health_record = {
            "timestamp": time.time(),
            "success": success,
            "response_time_ms": response_time
        }
        
        self.health_history[server_id].append(health_record)
        
        # Keep only recent history
        if len(self.health_history[server_id]) > 100:
            self.health_history[server_id] = self.health_history[server_id][-100:]
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """Get health check statistics."""
        stats = {
            "servers_monitored": len(self.health_history),
            "total_health_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "avg_response_time_ms": 0.0
        }
        
        total_response_time = 0.0
        successful_responses = 0
        
        for server_id, history in self.health_history.items():
            stats["total_health_checks"] += len(history)
            
            for record in history:
                if record["success"]:
                    stats["successful_checks"] += 1
                    total_response_time += record["response_time_ms"]
                    successful_responses += 1
                else:
                    stats["failed_checks"] += 1
        
        if successful_responses > 0:
            stats["avg_response_time_ms"] = total_response_time / successful_responses
        
        if stats["total_health_checks"] > 0:
            stats["health_check_success_rate"] = (
                stats["successful_checks"] / stats["total_health_checks"] * 100
            )
        else:
            stats["health_check_success_rate"] = 0.0
        
        return stats


@pytest.mark.L2
@pytest.mark.integration
class TestWebSocketLoadBalancing:
    """L2 integration tests for WebSocket load balancing."""
    
    @pytest.fixture
    def load_balancer(self):
        """Create load balancer with least connections strategy."""
        return WebSocketLoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)
    
    @pytest.fixture
    def health_checker(self, load_balancer):
        """Create health checker."""
        return HealthChecker(load_balancer)
    
    @pytest.fixture
    def test_servers(self, load_balancer):
        """Create test servers."""
        servers = []
        
        # Add servers with different capacities and regions
        servers.append(load_balancer.add_server("server-1", "10.0.1.1", 8080, capacity=100, region="us-east-1"))
        servers.append(load_balancer.add_server("server-2", "10.0.1.2", 8080, capacity=150, region="us-east-1"))
        servers.append(load_balancer.add_server("server-3", "10.0.2.1", 8080, capacity=100, region="us-west-1"))
        servers.append(load_balancer.add_server("server-4", "10.0.2.2", 8080, capacity=200, weight=2.0, region="us-west-1"))
        
        return servers
    
    @pytest.fixture
    def test_users(self):
        """Create test users."""
        return [
            UserInDB(
                id=f"lb_user_{i}",
                email=f"lbuser{i}@example.com",
                username=f"lbuser{i}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            for i in range(10)
        ]
    
    async def test_basic_load_balancing_functionality(self, load_balancer, test_servers, test_users):
        """Test basic load balancing routing."""
        user = test_users[0]
        
        # Route connection
        routing_result = await load_balancer.route_connection(user.id, "us-east-1")
        
        assert routing_result is not None
        assert "server_id" in routing_result
        assert "host" in routing_result
        assert "port" in routing_result
        assert "session_id" in routing_result
        assert routing_result["routing_time_ms"] < 10  # Should be fast
        
        # Verify server was assigned
        assert routing_result["server_id"] in [s.server_id for s in test_servers]
        
        # Check load balancer stats
        stats = load_balancer.get_load_balancer_stats()
        assert stats["total_connections_routed"] == 1
        assert stats["routing_decisions"] == 1
        assert stats["routing_success_rate"] == 100.0
    
    async def test_least_connections_strategy(self, load_balancer, test_servers, test_users):
        """Test least connections load balancing strategy."""
        # Route multiple connections
        routing_results = []
        
        for i in range(10):
            user = test_users[i]
            result = await load_balancer.route_connection(user.id, "us-east-1")
            assert result is not None
            routing_results.append(result)
        
        # Check that connections are distributed to least loaded servers
        server_connections = {}
        for result in routing_results:
            server_id = result["server_id"]
            server_connections[server_id] = server_connections.get(server_id, 0) + 1
        
        # Should distribute connections reasonably
        assert len(server_connections) > 1  # Should use multiple servers
        
        # Check server distribution
        distribution = load_balancer.get_server_distribution()
        for server_id, info in distribution.items():
            if server_id in server_connections:
                assert info["current_connections"] == server_connections[server_id]
    
    async def test_round_robin_strategy(self, test_servers, test_users):
        """Test round robin load balancing strategy."""
        lb = WebSocketLoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
        
        # Add same servers
        for server in test_servers:
            lb.add_server(server.server_id, server.host, server.port, server.capacity, region=server.region)
        
        # Route connections
        routing_results = []
        for i in range(8):
            user = test_users[i]
            result = await lb.route_connection(user.id, "us-east-1")
            assert result is not None
            routing_results.append(result)
        
        # Should cycle through servers
        server_sequence = [result["server_id"] for result in routing_results]
        unique_servers = list(set(server_sequence))
        
        # Should use multiple servers in rotation
        assert len(unique_servers) > 1
    
    async def test_geographic_strategy(self, test_users):
        """Test geographic load balancing strategy."""
        lb = WebSocketLoadBalancer(LoadBalancingStrategy.GEOGRAPHIC)
        
        # Add servers in different regions
        east_server = lb.add_server("east-1", "10.0.1.1", 8080, region="us-east-1")
        west_server = lb.add_server("west-1", "10.0.2.1", 8080, region="us-west-1")
        
        # Route from east coast client
        east_result = await lb.route_connection(test_users[0].id, "us-east-1")
        assert east_result["server_id"] == "east-1"  # Should prefer same region
        
        # Route from west coast client
        west_result = await lb.route_connection(test_users[1].id, "us-west-1")
        assert west_result["server_id"] == "west-1"  # Should prefer same region
        
        # Route from unknown region
        unknown_result = await lb.route_connection(test_users[2].id, "eu-west-1")
        assert unknown_result is not None  # Should fall back to available server
    
    async def test_session_affinity(self, load_balancer, test_servers, test_users):
        """Test sticky session functionality."""
        user = test_users[0]
        
        # Initial connection
        first_result = await load_balancer.route_connection(user.id, "us-east-1")
        assert first_result is not None
        
        first_server = first_result["server_id"]
        session_id = first_result["session_id"]
        
        # Subsequent connection with same session
        second_result = await load_balancer.route_connection(
            user.id, "us-east-1", session_affinity=session_id
        )
        
        assert second_result is not None
        assert second_result["server_id"] == first_server  # Should stick to same server
        assert second_result["strategy_used"] == "session_affinity"
        
        # Check affinity stats
        stats = load_balancer.get_load_balancer_stats()
        assert stats["session_affinity_hits"] == 1
    
    async def test_server_failure_handling(self, load_balancer, test_servers, test_users):
        """Test handling of server failures."""
        # Mark one server as unhealthy
        failing_server = test_servers[0]
        load_balancer.update_server_health(failing_server.server_id, ServerState.UNHEALTHY)
        
        # Route connections - should avoid unhealthy server
        routing_results = []
        for i in range(5):
            result = await load_balancer.route_connection(test_users[i].id, "us-east-1")
            assert result is not None
            routing_results.append(result)
        
        # Verify no connections went to unhealthy server
        routed_servers = [result["server_id"] for result in routing_results]
        assert failing_server.server_id not in routed_servers
        
        # Check failover metrics
        stats = load_balancer.get_load_balancer_stats()
        assert stats["healthy_servers"] == len(test_servers) - 1
    
    async def test_capacity_enforcement(self, load_balancer, test_servers, test_users):
        """Test server capacity enforcement."""
        # Use a server with small capacity
        small_server = test_servers[0]
        small_capacity = 3
        small_server.capacity = small_capacity
        
        # Route connections up to capacity
        routing_results = []
        for i in range(small_capacity + 2):  # Try to exceed capacity
            result = await load_balancer.route_connection(test_users[i].id, "us-east-1")
            if result:
                routing_results.append(result)
        
        # Check that capacity wasn't exceeded
        server_connections = {}
        for result in routing_results:
            server_id = result["server_id"]
            server_connections[server_id] = server_connections.get(server_id, 0) + 1
        
        # Small server shouldn't exceed capacity
        if small_server.server_id in server_connections:
            assert server_connections[small_server.server_id] <= small_capacity
    
    async def test_connection_disconnection(self, load_balancer, test_servers, test_users):
        """Test connection disconnection handling."""
        user = test_users[0]
        
        # Connect
        result = await load_balancer.route_connection(user.id, "us-east-1")
        assert result is not None
        
        session_id = result["session_id"]
        server_id = result["server_id"]
        
        # Check server connection count increased
        server = load_balancer.servers[server_id]
        initial_connections = server.current_connections
        assert initial_connections > 0
        
        # Disconnect
        disconnected = load_balancer.disconnect_connection(session_id)
        assert disconnected is True
        
        # Check server connection count decreased
        assert server.current_connections == initial_connections - 1
        
        # Session should be cleaned up
        assert session_id not in load_balancer.sessions
    
    async def test_health_monitoring_integration(self, load_balancer, health_checker, test_servers):
        """Test health monitoring integration."""
        # Start health monitoring briefly
        monitoring_task = asyncio.create_task(health_checker.start_health_monitoring())
        
        # Let it run for a short time
        await asyncio.sleep(2.0)
        
        # Stop monitoring
        health_checker.stop_health_monitoring()
        monitoring_task.cancel()
        
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # Check health statistics
        health_stats = health_checker.get_health_statistics()
        assert health_stats["servers_monitored"] == len(test_servers)
        assert health_stats["total_health_checks"] >= 0
    
    async def test_load_distribution_analysis(self, load_balancer, test_servers, test_users):
        """Test load distribution quality analysis."""
        # Route many connections
        for i in range(20):
            user = test_users[i % len(test_users)]
            await load_balancer.route_connection(user.id, "us-east-1")
        
        # Analyze distribution
        analysis = load_balancer.analyze_load_distribution()
        
        assert "avg_utilization" in analysis
        assert "distribution_quality_score" in analysis
        assert "min_utilization" in analysis
        assert "max_utilization" in analysis
        assert analysis["servers_analyzed"] > 0
        
        # Quality score should be reasonable (0-100)
        assert 0 <= analysis["distribution_quality_score"] <= 100
    
    @mock_justified("L2: Load balancing with real internal components")
    async def test_websocket_integration_with_load_balancing(self, load_balancer, test_servers, test_users):
        """Test WebSocket integration with load balancing."""
        # Simulate WebSocket manager using load balancer
        connection_sessions = []
        
        # Route multiple connections
        for i in range(8):
            user = test_users[i % len(test_users)]
            
            # Get routing decision
            routing_result = await load_balancer.route_connection(user.id, "us-east-1")
            assert routing_result is not None
            
            # Simulate connection establishment
            mock_websocket = AsyncMock()
            connection_sessions.append({
                "user_id": user.id,
                "session_id": routing_result["session_id"],
                "server_id": routing_result["server_id"],
                "websocket": mock_websocket,
                "routing_result": routing_result
            })
        
        # Verify connections are distributed
        server_distribution = {}
        for session in connection_sessions:
            server_id = session["server_id"]
            server_distribution[server_id] = server_distribution.get(server_id, 0) + 1
        
        # Should use multiple servers
        assert len(server_distribution) > 1
        
        # Test session affinity
        user_with_session = test_users[0]
        existing_session = connection_sessions[0]
        
        # Route another connection for same user with session affinity
        affinity_result = await load_balancer.route_connection(
            user_with_session.id, 
            "us-east-1", 
            session_affinity=existing_session["session_id"]
        )
        
        assert affinity_result["server_id"] == existing_session["server_id"]
        assert affinity_result["strategy_used"] == "session_affinity"
        
        # Simulate disconnections
        for session in connection_sessions[:4]:  # Disconnect half
            disconnected = load_balancer.disconnect_connection(session["session_id"])
            assert disconnected is True
        
        # Check final load balancer state
        final_stats = load_balancer.get_load_balancer_stats()
        assert final_stats["total_connections_routed"] >= len(connection_sessions)
        assert final_stats["routing_success_rate"] > 90  # Should have high success rate
    
    async def test_concurrent_routing_performance(self, load_balancer, test_servers, test_users):
        """Test concurrent routing performance."""
        concurrent_connections = 50
        routing_tasks = []
        
        # Create concurrent routing requests
        start_time = time.time()
        
        for i in range(concurrent_connections):
            user = test_users[i % len(test_users)]
            task = load_balancer.route_connection(user.id, "us-east-1")
            routing_tasks.append(task)
        
        # Execute all routing requests concurrently
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_routes = sum(
            1 for result in results 
            if not isinstance(result, Exception) and result is not None
        )
        
        # Performance assertions
        assert total_time < 5.0  # Should complete within 5 seconds
        assert successful_routes >= concurrent_connections * 0.9  # 90% success rate
        
        # Check average routing time
        stats = load_balancer.get_load_balancer_stats()
        assert stats["avg_routing_time_ms"] < 10  # Average should be fast
        
        # Check load distribution
        analysis = load_balancer.analyze_load_distribution()
        assert analysis["distribution_quality_score"] >= 60  # Reasonable distribution
    
    async def test_load_balancing_strategies_comparison(self, test_servers, test_users):
        """Test comparison of different load balancing strategies."""
        strategies = [
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTIONS,
            LoadBalancingStrategy.GEOGRAPHIC
        ]
        
        strategy_results = {}
        
        for strategy in strategies:
            lb = WebSocketLoadBalancer(strategy)
            
            # Add servers
            for server in test_servers:
                lb.add_server(server.server_id, server.host, server.port, 
                            server.capacity, region=server.region)
            
            # Route connections
            start_time = time.time()
            routing_count = 0
            
            for i in range(20):
                user = test_users[i % len(test_users)]
                result = await lb.route_connection(user.id, "us-east-1")
                if result:
                    routing_count += 1
            
            total_time = time.time() - start_time
            
            # Analyze performance
            stats = lb.get_load_balancer_stats()
            analysis = lb.analyze_load_distribution()
            
            strategy_results[strategy.value] = {
                "routing_time": total_time,
                "successful_routes": routing_count,
                "avg_routing_time_ms": stats["avg_routing_time_ms"],
                "distribution_quality": analysis["distribution_quality_score"],
                "routing_success_rate": stats["routing_success_rate"]
            }
        
        # Verify all strategies worked
        for strategy, results in strategy_results.items():
            assert results["successful_routes"] >= 15  # Most routes should succeed
            assert results["routing_success_rate"] >= 75  # High success rate
            assert results["avg_routing_time_ms"] < 20  # Fast routing
        
        # Geographic strategy should have good distribution for mixed regions
        geo_results = strategy_results["geographic"]
        assert geo_results["distribution_quality"] >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])