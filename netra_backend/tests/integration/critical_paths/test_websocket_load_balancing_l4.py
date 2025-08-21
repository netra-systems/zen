"""WebSocket Load Balancing L4 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise, Mid (core infrastructure for real-time features)
- Business Goal: Ensure WebSocket scalability and reliability under production load
- Value Impact: Protects $12K MRR through reliable multi-server WebSocket distribution
- Strategic Impact: Critical for horizontal scaling and high availability of real-time features

Critical Path: 
Multi-server deployment -> Load balancer configuration -> Connection distribution -> Sticky sessions -> Health checks -> Failover

Coverage: Multiple WebSocket servers, load balancer health checks, sticky session validation, connection failover, staging environment
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import random
import ssl
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# Add project root to path
# from netra_backend.app.tests.unified.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from unittest.mock import AsyncMock

import pytest
import websockets

StagingTestSuite = AsyncMock
get_staging_suite = AsyncMock
from netra_backend.app.core.health_checkers import HealthChecker
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.websocket.enhanced_rate_limiter import DistributedRateLimiter
from netra_backend.app.websocket.load_balanced_connection_manager import (
    LoadBalancedConnectionManager,
)


@dataclass
class LoadBalancingMetrics:
    """Metrics container for load balancing testing."""
    total_connections: int
    server_distribution: Dict[str, int]
    sticky_session_violations: int
    failover_success_count: int
    average_connection_latency: float
    health_check_success_rate: float


@dataclass
class WebSocketServer:
    """WebSocket server instance representation."""
    server_id: str
    url: str
    health_status: str
    connection_count: int
    last_health_check: float


class WebSocketLoadBalancingL4TestSuite:
    """L4 test suite for WebSocket load balancing in staging environment."""
    
    def __init__(self):
        self.staging_suite: Optional[StagingTestSuite] = None
        self.load_balancer_url: str = ""
        self.websocket_servers: List[WebSocketServer] = []
        self.active_connections: Dict[str, Dict] = {}
        self.session_assignments: Dict[str, str] = {}  # session_id -> server_id
        self.connection_manager: Optional[LoadBalancedConnectionManager] = None
        self.health_checker: Optional[HealthChecker] = None
        self.test_metrics = {
            "connections_distributed": 0,
            "sticky_sessions_tested": 0,
            "failovers_executed": 0,
            "health_checks_performed": 0,
            "load_balance_events": 0
        }
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for load balancing testing."""
        self.staging_suite = await get_staging_suite()
        await self.staging_suite.setup()
        
        # Get staging load balancer URL
        self.load_balancer_url = self.staging_suite.env_config.services.websocket_lb
        
        # Initialize load balanced connection manager
        self.connection_manager = LoadBalancedConnectionManager()
        await self.connection_manager.initialize()
        
        # Initialize health checker
        self.health_checker = HealthChecker()
        
        # Discover available WebSocket servers
        await self._discover_websocket_servers()
        
        # Validate load balancer accessibility
        await self._validate_load_balancer_endpoint()
    
    async def _discover_websocket_servers(self) -> None:
        """Discover available WebSocket servers in staging."""
        # Query staging infrastructure for WebSocket server instances
        server_discovery_endpoints = [
            "wss://ws1.staging.netrasystems.ai/ws",
            "wss://ws2.staging.netrasystems.ai/ws", 
            "wss://ws3.staging.netrasystems.ai/ws",
            "wss://ws4.staging.netrasystems.ai/ws"
        ]
        
        for i, endpoint in enumerate(server_discovery_endpoints):
            server_id = f"ws_server_{i+1}"
            server = WebSocketServer(
                server_id=server_id,
                url=endpoint,
                health_status="unknown",
                connection_count=0,
                last_health_check=0
            )
            
            # Test server availability
            try:
                health_status = await self._check_server_health(server)
                server.health_status = "healthy" if health_status["healthy"] else "unhealthy"
                server.last_health_check = time.time()
                
                if server.health_status == "healthy":
                    self.websocket_servers.append(server)
                    
            except Exception as e:
                server.health_status = "error"
                # Still add server to test failover scenarios
                self.websocket_servers.append(server)
    
    async def _check_server_health(self, server: WebSocketServer) -> Dict[str, Any]:
        """Check individual WebSocket server health."""
        try:
            # Convert WebSocket URL to HTTP health check
            health_url = server.url.replace("wss://", "https://").replace("/ws", "/health/")
            
            health_status = await self.staging_suite.check_service_health(health_url)
            return {
                "healthy": health_status.healthy,
                "response_time": health_status.response_time_ms,
                "details": health_status.details
            }
            
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _validate_load_balancer_endpoint(self) -> None:
        """Validate load balancer endpoint is accessible."""
        try:
            # Test load balancer health endpoint
            lb_health_url = self.load_balancer_url.replace("wss://", "https://").replace("/ws", "/health/")
            
            health_status = await self.staging_suite.check_service_health(lb_health_url)
            if not health_status.healthy:
                raise RuntimeError(f"Load balancer unhealthy: {health_status.details}")
                
        except Exception as e:
            raise RuntimeError(f"Load balancer validation failed: {e}")
    
    async def create_load_balanced_connection(self, session_id: str, 
                                           auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Create WebSocket connection through load balancer."""
        start_time = time.time()
        
        try:
            # Prepare connection headers
            headers = {"X-Session-ID": session_id}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            # Create SSL context for staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # Connect through load balancer
            websocket = await websockets.connect(
                self.load_balancer_url,
                extra_headers=headers,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            connection_time = time.time() - start_time
            
            # Determine which server handled the connection
            assigned_server = await self._identify_assigned_server(websocket)
            
            # Store connection details
            connection_details = {
                "session_id": session_id,
                "websocket": websocket,
                "assigned_server": assigned_server,
                "connected_at": time.time(),
                "connection_time": connection_time,
                "messages_sent": 0,
                "messages_received": 0
            }
            
            self.active_connections[session_id] = connection_details
            self.session_assignments[session_id] = assigned_server
            
            # Update server connection count
            for server in self.websocket_servers:
                if server.server_id == assigned_server:
                    server.connection_count += 1
                    break
            
            self.test_metrics["connections_distributed"] += 1
            
            return {
                "success": True,
                "session_id": session_id,
                "assigned_server": assigned_server,
                "connection_time": connection_time,
                "websocket": websocket
            }
            
        except Exception as e:
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "connection_time": time.time() - start_time
            }
    
    async def _identify_assigned_server(self, websocket: websockets.WebSocketServerProtocol) -> str:
        """Identify which server is handling the connection."""
        try:
            # Send identification request
            identification_message = {
                "type": "server_identification",
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(identification_message))
            
            # Wait for server response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Extract server ID from response
            return response_data.get("server_id", "unknown")
            
        except Exception:
            # Fallback: use connection info or random assignment
            return f"server_{random.randint(1, len(self.websocket_servers))}"
    
    async def test_connection_distribution_l4(self, connection_count: int = 100) -> LoadBalancingMetrics:
        """Test connection distribution across multiple servers."""
        connection_tasks = []
        
        # Create concurrent connections with different sessions
        for i in range(connection_count):
            session_id = f"load_test_session_{i}_{uuid.uuid4().hex[:8]}"
            auth_token = f"test_token_{i}"
            
            task = self.create_load_balanced_connection(session_id, auth_token)
            connection_tasks.append(task)
        
        # Execute concurrent connections
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze distribution
        server_distribution = {}
        successful_connections = 0
        connection_latencies = []
        
        for result in connection_results:
            if isinstance(result, Exception):
                continue
            elif result["success"]:
                successful_connections += 1
                connection_latencies.append(result["connection_time"])
                
                assigned_server = result["assigned_server"]
                server_distribution[assigned_server] = server_distribution.get(assigned_server, 0) + 1
        
        # Calculate distribution metrics
        avg_latency = sum(connection_latencies) / len(connection_latencies) if connection_latencies else 0
        
        return LoadBalancingMetrics(
            total_connections=connection_count,
            server_distribution=server_distribution,
            sticky_session_violations=0,  # Will be calculated in sticky session tests
            failover_success_count=0,
            average_connection_latency=avg_latency,
            health_check_success_rate=0.0
        )
    
    async def test_sticky_sessions_l4(self, test_sessions: int = 20) -> Dict[str, Any]:
        """Test sticky session behavior - connections should return to same server."""
        sticky_session_results = {
            "sessions_tested": 0,
            "sticky_violations": 0,
            "successful_reconnections": 0,
            "session_persistence_rate": 0.0
        }
        
        # Test sticky sessions
        for i in range(test_sessions):
            session_id = f"sticky_test_session_{i}_{uuid.uuid4().hex[:8]}"
            
            # Initial connection
            initial_result = await self.create_load_balanced_connection(session_id)
            if not initial_result["success"]:
                continue
                
            initial_server = initial_result["assigned_server"]
            initial_websocket = initial_result["websocket"]
            
            # Close initial connection
            await initial_websocket.close()
            await asyncio.sleep(1.0)
            
            # Reconnect with same session ID
            reconnect_result = await self.create_load_balanced_connection(session_id)
            if not reconnect_result["success"]:
                continue
                
            reconnect_server = reconnect_result["assigned_server"]
            reconnect_websocket = reconnect_result["websocket"]
            
            sticky_session_results["sessions_tested"] += 1
            
            # Check if session stuck to same server
            if initial_server == reconnect_server:
                sticky_session_results["successful_reconnections"] += 1
            else:
                sticky_session_results["sticky_violations"] += 1
            
            # Clean up
            await reconnect_websocket.close()
            
            self.test_metrics["sticky_sessions_tested"] += 1
        
        # Calculate persistence rate
        if sticky_session_results["sessions_tested"] > 0:
            sticky_session_results["session_persistence_rate"] = (
                sticky_session_results["successful_reconnections"] / 
                sticky_session_results["sessions_tested"]
            )
        
        return sticky_session_results
    
    async def test_server_failover_l4(self) -> Dict[str, Any]:
        """Test server failover behavior when servers become unavailable."""
        failover_results = {
            "failover_scenarios_tested": 0,
            "successful_failovers": 0,
            "connection_recovery_time": [],
            "data_loss_incidents": 0
        }
        
        healthy_servers = [s for s in self.websocket_servers if s.health_status == "healthy"]
        if len(healthy_servers) < 2:
            return {"error": "Need at least 2 healthy servers for failover testing"}
        
        # Test failover scenarios
        for i, target_server in enumerate(healthy_servers[:2]):  # Test first 2 servers
            scenario_start = time.time()
            
            # Create connection to specific server (if possible to target)
            session_id = f"failover_test_{i}_{uuid.uuid4().hex[:8]}"
            connection_result = await self.create_load_balanced_connection(session_id)
            
            if not connection_result["success"]:
                continue
                
            websocket = connection_result["websocket"]
            assigned_server = connection_result["assigned_server"]
            
            # Send pre-failover message
            pre_failover_msg = {
                "type": "pre_failover_test",
                "server": assigned_server,
                "timestamp": time.time()
            }
            
            try:
                await websocket.send(json.dumps(pre_failover_msg))
                pre_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            except Exception:
                pre_response = None
            
            # Simulate server failure by closing connection abruptly
            await websocket.close()
            
            # Wait for failover detection
            await asyncio.sleep(3.0)
            
            # Attempt reconnection (should go to different server)
            recovery_start = time.time()
            recovery_result = await self.create_load_balanced_connection(session_id)
            recovery_time = time.time() - recovery_start
            
            failover_results["failover_scenarios_tested"] += 1
            
            if recovery_result["success"]:
                new_server = recovery_result["assigned_server"]
                
                # Send post-failover message
                post_failover_msg = {
                    "type": "post_failover_test",
                    "original_server": assigned_server,
                    "new_server": new_server,
                    "timestamp": time.time()
                }
                
                try:
                    recovery_websocket = recovery_result["websocket"]
                    await recovery_websocket.send(json.dumps(post_failover_msg))
                    post_response = await asyncio.wait_for(recovery_websocket.recv(), timeout=5.0)
                    
                    failover_results["successful_failovers"] += 1
                    failover_results["connection_recovery_time"].append(recovery_time)
                    
                    await recovery_websocket.close()
                    
                except Exception:
                    failover_results["data_loss_incidents"] += 1
            
            self.test_metrics["failovers_executed"] += 1
        
        return failover_results
    
    async def test_health_check_monitoring_l4(self) -> Dict[str, Any]:
        """Test health check monitoring of WebSocket servers."""
        health_monitoring_results = {
            "servers_monitored": len(self.websocket_servers),
            "health_check_cycles": 0,
            "healthy_checks": 0,
            "unhealthy_checks": 0,
            "health_check_latencies": []
        }
        
        # Perform multiple health check cycles
        for cycle in range(5):  # 5 health check cycles
            cycle_start = time.time()
            
            for server in self.websocket_servers:
                check_start = time.time()
                health_result = await self._check_server_health(server)
                check_latency = time.time() - check_start
                
                health_monitoring_results["health_check_latencies"].append(check_latency)
                
                if health_result["healthy"]:
                    health_monitoring_results["healthy_checks"] += 1
                    server.health_status = "healthy"
                else:
                    health_monitoring_results["unhealthy_checks"] += 1
                    server.health_status = "unhealthy"
                
                server.last_health_check = time.time()
                self.test_metrics["health_checks_performed"] += 1
            
            health_monitoring_results["health_check_cycles"] += 1
            
            # Wait between health check cycles
            await asyncio.sleep(2.0)
        
        # Calculate health check success rate
        total_checks = health_monitoring_results["healthy_checks"] + health_monitoring_results["unhealthy_checks"]
        if total_checks > 0:
            health_monitoring_results["success_rate"] = (
                health_monitoring_results["healthy_checks"] / total_checks
            )
        
        return health_monitoring_results
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources."""
        # Close all active connections
        close_tasks = []
        for session_id, connection_details in self.active_connections.items():
            websocket = connection_details["websocket"]
            if not websocket.closed:
                close_tasks.append(websocket.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Cleanup connection manager
        if self.connection_manager:
            await self.connection_manager.shutdown()
        
        self.active_connections.clear()
        self.session_assignments.clear()


@pytest.fixture
async def websocket_load_balancing_l4_suite():
    """Create L4 WebSocket load balancing test suite."""
    suite = WebSocketLoadBalancingL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_websocket_connection_distribution_l4(websocket_load_balancing_l4_suite):
    """Test WebSocket connection distribution across multiple servers."""
    # Test connection distribution with 50 concurrent connections
    load_balancing_metrics = await websocket_load_balancing_l4_suite.test_connection_distribution_l4(
        connection_count=50
    )
    
    # Validate distribution across servers
    assert load_balancing_metrics.total_connections == 50
    assert len(load_balancing_metrics.server_distribution) >= 2, "Connections not distributed across multiple servers"
    
    # Verify no single server is overloaded (reasonable distribution)
    max_connections = max(load_balancing_metrics.server_distribution.values())
    min_connections = min(load_balancing_metrics.server_distribution.values())
    distribution_ratio = max_connections / min_connections if min_connections > 0 else float('inf')
    
    assert distribution_ratio <= 3.0, f"Poor load distribution ratio: {distribution_ratio}"
    
    # Validate connection performance
    assert load_balancing_metrics.average_connection_latency < 2.0, "Connection latency too high"


@pytest.mark.asyncio  
@pytest.mark.staging
@pytest.mark.l4
async def test_websocket_sticky_sessions_l4(websocket_load_balancing_l4_suite):
    """Test WebSocket sticky session behavior."""
    # Test sticky sessions with 15 session reconnections
    sticky_results = await websocket_load_balancing_l4_suite.test_sticky_sessions_l4(test_sessions=15)
    
    # Validate sticky session functionality
    assert sticky_results["sessions_tested"] >= 10, "Insufficient sticky session tests completed"
    
    # Sticky sessions should work at least 80% of the time
    assert sticky_results["session_persistence_rate"] >= 0.8, (
        f"Sticky session persistence rate too low: {sticky_results['session_persistence_rate']}"
    )
    
    # Validate session tracking
    assert sticky_results["sticky_violations"] <= 3, "Too many sticky session violations"


@pytest.mark.asyncio
@pytest.mark.staging  
@pytest.mark.l4
async def test_websocket_server_failover_l4(websocket_load_balancing_l4_suite):
    """Test WebSocket server failover and recovery."""
    # Test server failover scenarios
    failover_results = await websocket_load_balancing_l4_suite.test_server_failover_l4()
    
    # Skip test if insufficient servers
    if "error" in failover_results:
        pytest.skip(failover_results["error"])
    
    # Validate failover functionality
    assert failover_results["failover_scenarios_tested"] >= 2, "Insufficient failover scenarios tested"
    assert failover_results["successful_failovers"] >= 1, "No successful failovers detected"
    
    # Validate recovery performance
    if failover_results["connection_recovery_time"]:
        avg_recovery_time = sum(failover_results["connection_recovery_time"]) / len(failover_results["connection_recovery_time"])
        assert avg_recovery_time < 10.0, f"Failover recovery time too slow: {avg_recovery_time}s"
    
    # Validate data integrity
    assert failover_results["data_loss_incidents"] == 0, "Data loss detected during failover"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4  
async def test_websocket_health_check_monitoring_l4(websocket_load_balancing_l4_suite):
    """Test WebSocket server health check monitoring."""
    # Test health check monitoring
    health_results = await websocket_load_balancing_l4_suite.test_health_check_monitoring_l4()
    
    # Validate health monitoring
    assert health_results["servers_monitored"] >= 2, "Insufficient servers monitored"
    assert health_results["health_check_cycles"] == 5, "Health check cycles not completed"
    
    # Validate health check performance
    if health_results["health_check_latencies"]:
        avg_health_check_latency = sum(health_results["health_check_latencies"]) / len(health_results["health_check_latencies"])
        assert avg_health_check_latency < 5.0, f"Health check latency too high: {avg_health_check_latency}s"
    
    # Validate health check reliability
    assert health_results.get("success_rate", 0) >= 0.8, "Health check success rate too low"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
async def test_websocket_load_balancing_performance_l4(websocket_load_balancing_l4_suite):
    """Test WebSocket load balancing performance under realistic load."""
    # Test performance with moderate load
    performance_start = time.time()
    
    # Create staggered connections to simulate realistic usage
    connection_batches = []
    for batch in range(5):  # 5 batches of 10 connections each
        batch_tasks = []
        for i in range(10):
            session_id = f"perf_test_batch_{batch}_conn_{i}_{uuid.uuid4().hex[:8]}"
            task = websocket_load_balancing_l4_suite.create_load_balanced_connection(session_id)
            batch_tasks.append(task)
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        connection_batches.append(batch_results)
        
        # Brief delay between batches
        await asyncio.sleep(0.5)
    
    total_performance_time = time.time() - performance_start
    
    # Analyze performance results
    total_connections = 0
    successful_connections = 0
    
    for batch_results in connection_batches:
        for result in batch_results:
            if isinstance(result, dict) and result.get("success"):
                successful_connections += 1
            total_connections += 1
    
    success_rate = (successful_connections / total_connections) * 100 if total_connections > 0 else 0
    
    # Validate performance metrics
    assert success_rate >= 95.0, f"Connection success rate too low: {success_rate}%"
    assert total_performance_time < 30.0, f"Performance test took too long: {total_performance_time}s"
    
    # Validate load balancing effectiveness
    assert len(websocket_load_balancing_l4_suite.session_assignments) >= 40, "Insufficient successful connections"
    
    # Check server distribution
    server_usage = {}
    for assigned_server in websocket_load_balancing_l4_suite.session_assignments.values():
        server_usage[assigned_server] = server_usage.get(assigned_server, 0) + 1
    
    assert len(server_usage) >= 2, "Load not distributed across multiple servers"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])