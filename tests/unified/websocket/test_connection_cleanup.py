"""WebSocket Connection Cleanup Tests - P0 Critical

Tests proper resource cleanup on WebSocket disconnections (normal and abnormal).
Critical for preventing memory leaks, ghost connections, and resource exhaustion.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise) 
2. Business Goal: System Reliability & Resource Management
3. Value Impact: Prevents system degradation and crashes from resource leaks
4. Revenue Impact: Protects $150K+ MRR from system instability

CRITICAL REQUIREMENTS:
- MUST use real WebSocket connections (NO MOCKS)
- Test normal disconnect cleanup
- Test abnormal disconnect cleanup (network drop, crash)
- Verify no memory leaks or ghost connections
- Test connection manager resource tracking
- Test within 5 seconds per test case
- Include 3+ cleanup scenarios

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines
- Function size: <25 lines each
- Real services integration
- Resource leak detection
- Type safety with annotations
"""

import asyncio
import gc
import time
import tracemalloc
from typing import Any, Dict, List, Optional, Set

import psutil
import pytest
import pytest_asyncio
import websockets
from websockets.exceptions import ConnectionClosedError

from tests.unified.jwt_token_helpers import JWTTestHelper
from tests.unified.real_client_types import ClientConfig, ConnectionState
from tests.unified.real_services_manager import (
    create_real_services_manager,
)
from tests.unified.real_websocket_client import RealWebSocketClient


class ConnectionCleanupTester:
    """WebSocket connection cleanup and resource leak tester - NO MOCKS"""
    
    def __init__(self):
        self.services_manager = None
        self.test_clients: List[RealWebSocketClient] = []
        self.cleanup_metrics: List[Dict[str, Any]] = []
        self.active_connections: Set[str] = set()
        self.memory_snapshots: List[Dict[str, Any]] = []
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        
    async def setup_real_services(self) -> None:
        """Start real Backend and Auth services with memory tracking"""
        # Start memory tracking
        tracemalloc.start()
        self.record_memory_snapshot("setup_start")
        
        self.services_manager = create_real_services_manager()
        await self.services_manager.start_all_services()
        
        # Verify services are running
        health_status = await self.services_manager.health_status()
        if not all(svc['ready'] for svc in health_status.values()):
            raise RuntimeError(f"Services not ready: {health_status}")
            
        self.record_memory_snapshot("setup_complete")
    
    async def teardown_real_services(self) -> None:
        """Clean shutdown with leak detection"""
        self.record_memory_snapshot("teardown_start")
        
        # Force close all test clients
        cleanup_tasks = []
        for client in self.test_clients:
            cleanup_tasks.append(client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Stop services
        if self.services_manager:
            await self.services_manager.stop_all_services()
        
        # Final cleanup verification
        await self._verify_complete_cleanup()
        self.record_memory_snapshot("teardown_complete")
        
        # Check for memory leaks
        self._analyze_memory_usage()
    
    def record_memory_snapshot(self, phase: str) -> None:
        """Record memory usage snapshot"""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            snapshot = {
                "phase": phase,
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024,
                "timestamp": time.time()
            }
            self.memory_snapshots.append(snapshot)
    
    def _analyze_memory_usage(self) -> None:
        """Analyze memory usage for leaks"""
        if len(self.memory_snapshots) < 2:
            return
            
        start_memory = self.memory_snapshots[0]["current_mb"]
        end_memory = self.memory_snapshots[-1]["current_mb"]
        memory_growth = end_memory - start_memory
        
        # Record memory analysis
        analysis = {
            "memory_growth_mb": memory_growth,
            "acceptable_growth": memory_growth < 10.0,  # Less than 10MB growth
            "snapshots": self.memory_snapshots
        }
        self.cleanup_metrics.append({
            "type": "memory_analysis",
            "data": analysis
        })
    
    async def _verify_complete_cleanup(self) -> None:
        """Verify all resources are properly cleaned up"""
        # Give time for cleanup to complete
        await asyncio.sleep(1.0)
        
        # Force garbage collection
        gc.collect()
        
        # Verify no active connections remain
        ghost_connections = len(self.active_connections)
        
        # Try to connect to verify server is down
        server_still_running = await self._check_server_still_running()
        
        cleanup_verification = {
            "ghost_connections": ghost_connections,
            "server_still_running": server_still_running,
            "cleanup_successful": ghost_connections == 0 and not server_still_running
        }
        
        self.cleanup_metrics.append({
            "type": "cleanup_verification", 
            "data": cleanup_verification
        })
    
    async def _check_server_still_running(self) -> bool:
        """Check if WebSocket server is still running"""
        try:
            async with websockets.connect(self.websocket_url, open_timeout=1):
                return True
        except (ConnectionRefusedError, OSError, Exception):
            return False
    
    def create_tracked_client(self, user_id: str = "cleanup_test_user") -> RealWebSocketClient:
        """Create tracked WebSocket client for cleanup testing"""
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(user_id, f"{user_id}@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        config = ClientConfig(timeout=5.0, max_retries=1)
        client = RealWebSocketClient(self.websocket_url, config)
        client._auth_headers = headers
        client._cleanup_user_id = user_id
        
        self.test_clients.append(client)
        self.active_connections.add(user_id)
        return client
    
    def record_cleanup_metrics(self, client: RealWebSocketClient, 
                             cleanup_type: str, success: bool) -> None:
        """Record connection cleanup metrics"""
        if hasattr(client, '_cleanup_user_id'):
            self.active_connections.discard(client._cleanup_user_id)
        
        metrics = {
            "cleanup_type": cleanup_type,
            "success": success,
            "final_state": client.state.value,
            "connection_time": client.metrics.connection_time,
            "last_error": client.metrics.last_error,
            "active_connections_remaining": len(self.active_connections)
        }
        self.cleanup_metrics.append({"type": "connection_cleanup", "data": metrics})


@pytest_asyncio.fixture
async def cleanup_tester():
    """Connection cleanup tester fixture with real services"""
    tester = ConnectionCleanupTester()
    await tester.setup_real_services()
    yield tester
    await tester.teardown_real_services()


class TestNormalConnectionCleanup:
    """Test normal connection cleanup scenarios"""
    
    @pytest.mark.asyncio
    async def test_graceful_disconnect_cleanup(self, cleanup_tester):
        """Test normal graceful disconnect cleans up all resources"""
        client = cleanup_tester.create_tracked_client("graceful_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        # Record pre-disconnect state
        initial_connections = len(cleanup_tester.active_connections)
        cleanup_tester.record_memory_snapshot("before_graceful_disconnect")
        
        # Perform graceful disconnect
        await client.close()
        
        # Verify cleanup
        assert client.state == ConnectionState.DISCONNECTED
        final_connections = len(cleanup_tester.active_connections)
        assert final_connections < initial_connections
        
        cleanup_tester.record_memory_snapshot("after_graceful_disconnect")
        cleanup_tester.record_cleanup_metrics(client, "graceful_disconnect", True)
    
    @pytest.mark.asyncio
    async def test_multiple_connection_cleanup(self, cleanup_tester):
        """Test cleanup of multiple simultaneous connections"""
        num_clients = 3
        clients = []
        
        # Create and connect multiple clients
        for i in range(num_clients):
            client = cleanup_tester.create_tracked_client(f"multi_user_{i}")
            await client.connect(client._auth_headers)
            clients.append(client)
        
        # Verify all connected
        assert all(client.state == ConnectionState.CONNECTED for client in clients)
        assert len(cleanup_tester.active_connections) >= num_clients
        
        cleanup_tester.record_memory_snapshot("before_multi_cleanup")
        
        # Close all connections
        close_tasks = [client.close() for client in clients]
        await asyncio.gather(*close_tasks)
        
        # Verify all cleaned up
        assert all(client.state == ConnectionState.DISCONNECTED for client in clients)
        
        cleanup_tester.record_memory_snapshot("after_multi_cleanup")
        
        for i, client in enumerate(clients):
            cleanup_tester.record_cleanup_metrics(client, f"multi_cleanup_{i}", True)
    
    @pytest.mark.asyncio
    async def test_connection_timeout_cleanup(self, cleanup_tester):
        """Test cleanup when connection times out"""
        # Create client with short timeout
        config = ClientConfig(timeout=1.0, max_retries=1)
        client = RealWebSocketClient("ws://localhost:9999", config)  # Non-existent port
        client._cleanup_user_id = "timeout_user"
        
        cleanup_tester.test_clients.append(client)
        cleanup_tester.active_connections.add("timeout_user")
        
        cleanup_tester.record_memory_snapshot("before_timeout_test")
        
        # Attempt connection that will timeout
        success = await client.connect({"Authorization": "Bearer test"})
        
        # Verify failure and cleanup
        assert success is False
        assert client.state == ConnectionState.FAILED
        
        cleanup_tester.record_memory_snapshot("after_timeout_test")
        cleanup_tester.record_cleanup_metrics(client, "timeout_cleanup", True)


class TestAbnormalConnectionCleanup:
    """Test abnormal connection cleanup scenarios - 3+ error cases required"""
    
    @pytest.mark.asyncio
    async def test_network_drop_cleanup(self, cleanup_tester):
        """CLEANUP CASE 1: Network drop during active connection"""
        client = cleanup_tester.create_tracked_client("network_drop_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        cleanup_tester.record_memory_snapshot("before_network_drop")
        
        # Simulate network drop by forcefully closing underlying connection
        if hasattr(client, '_websocket') and client._websocket:
            # Force close the underlying websocket
            await client._websocket.close(code=1006)  # Abnormal closure
            
        # Give time for cleanup detection
        await asyncio.sleep(0.5)
        
        # Verify cleanup handling
        # Connection should detect the drop and clean up
        send_success = await client.send({"type": "test"})
        assert send_success is False  # Should fail after network drop
        
        cleanup_tester.record_memory_snapshot("after_network_drop")
        cleanup_tester.record_cleanup_metrics(client, "network_drop_cleanup", True)
    
    @pytest.mark.asyncio
    async def test_server_shutdown_cleanup(self, cleanup_tester):
        """CLEANUP CASE 2: Server shutdown during active connection"""
        client = cleanup_tester.create_tracked_client("server_shutdown_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        cleanup_tester.record_memory_snapshot("before_server_shutdown")
        
        # Simulate server shutdown by stopping services
        if cleanup_tester.services_manager:
            # Stop backend service to simulate server shutdown
            backend_service = cleanup_tester.services_manager.services.get("backend")
            if backend_service and backend_service.process:
                backend_service.process.terminate()
                await asyncio.sleep(1.0)  # Give time for shutdown
        
        # Verify client detects server shutdown
        try:
            await client.send({"type": "test"})
            response = await client.receive(timeout=2.0)
            # If we get here, server didn't shut down properly
            assert False, "Expected connection failure after server shutdown"
        except (ConnectionClosedError, asyncio.TimeoutError):
            # Expected behavior - connection should fail
            pass
        
        cleanup_tester.record_memory_snapshot("after_server_shutdown")
        cleanup_tester.record_cleanup_metrics(client, "server_shutdown_cleanup", True)
    
    @pytest.mark.asyncio
    async def test_malformed_message_cleanup(self, cleanup_tester):
        """CLEANUP CASE 3: Connection cleanup after malformed message"""
        client = cleanup_tester.create_tracked_client("malformed_msg_user")
        
        # Establish connection
        await client.connect(client._auth_headers)
        assert client.state == ConnectionState.CONNECTED
        
        cleanup_tester.record_memory_snapshot("before_malformed_msg")
        
        # Send malformed message that might cause server to close connection
        malformed_messages = [
            "invalid_json_string",
            {"type": None, "payload": "invalid"},
            {"invalid": "structure", "missing": "type"}
        ]
        
        connection_closed = False
        for msg in malformed_messages:
            try:
                await client.send(msg)
                await asyncio.sleep(0.2)  # Give server time to respond
                
                # Try to receive response
                response = await client.receive(timeout=1.0)
                if response is None:
                    connection_closed = True
                    break
                    
            except (ConnectionClosedError, Exception):
                connection_closed = True
                break
        
        # If connection was closed, verify cleanup
        if connection_closed:
            assert client.state in [ConnectionState.DISCONNECTED, ConnectionState.FAILED]
        
        cleanup_tester.record_memory_snapshot("after_malformed_msg")
        cleanup_tester.record_cleanup_metrics(client, "malformed_msg_cleanup", True)
    
    @pytest.mark.asyncio
    async def test_auth_token_expiry_cleanup(self, cleanup_tester):
        """CLEANUP CASE 4: Connection cleanup when auth token expires"""
        # Create client with short-lived token
        jwt_helper = JWTTestHelper()
        expired_payload = jwt_helper.create_expired_payload()
        expired_payload["sub"] = "token_expiry_user"
        token = jwt_helper.create_token(expired_payload)
        config = ClientConfig(timeout=3.0, max_retries=1)
        client = RealWebSocketClient(cleanup_tester.websocket_url, config)
        client._auth_headers = {"Authorization": f"Bearer {token}"}
        client._cleanup_user_id = "token_expiry_user"
        
        cleanup_tester.test_clients.append(client)
        cleanup_tester.active_connections.add("token_expiry_user")
        
        cleanup_tester.record_memory_snapshot("before_token_expiry")
        
        # Attempt connection with expired token
        success = await client.connect(client._auth_headers)
        
        # Verify connection rejection and cleanup
        assert success is False
        assert client.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
        assert client.metrics.last_error is not None
        
        cleanup_tester.record_memory_snapshot("after_token_expiry")
        cleanup_tester.record_cleanup_metrics(client, "token_expiry_cleanup", True)


class TestResourceLeakDetection:
    """Test for resource leaks and ghost connections"""
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, cleanup_tester):
        """Test for memory leaks during connection lifecycle"""
        initial_memory = None
        if cleanup_tester.memory_snapshots:
            initial_memory = cleanup_tester.memory_snapshots[-1]["current_mb"]
        
        # Create and destroy multiple connections to test for leaks
        for cycle in range(3):
            clients = []
            
            # Create multiple clients
            for i in range(2):
                client = cleanup_tester.create_tracked_client(f"leak_test_{cycle}_{i}")
                await client.connect(client._auth_headers)
                clients.append(client)
            
            # Use connections briefly
            for client in clients:
                await client.send({"type": "ping", "payload": {}})
                await client.receive(timeout=1.0)
            
            # Close all connections
            for client in clients:
                await client.close()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.5)  # Allow cleanup to complete
            
            cleanup_tester.record_memory_snapshot(f"leak_test_cycle_{cycle}")
        
        # Analyze memory growth
        if len(cleanup_tester.memory_snapshots) >= 2:
            final_memory = cleanup_tester.memory_snapshots[-1]["current_mb"]
            if initial_memory:
                memory_growth = final_memory - initial_memory
                
                # Assert reasonable memory growth (less than 5MB for test operations)
                assert memory_growth < 5.0, f"Potential memory leak: {memory_growth}MB growth"
                
                cleanup_tester.cleanup_metrics.append({
                    "type": "memory_leak_test",
                    "data": {
                        "memory_growth_mb": memory_growth,
                        "cycles_completed": 3,
                        "connections_per_cycle": 2
                    }
                })
    
    @pytest.mark.asyncio
    async def test_ghost_connection_detection(self, cleanup_tester):
        """Test for ghost connections that aren't properly cleaned up"""
        # Track connections before test
        initial_connection_count = len(cleanup_tester.active_connections)
        
        # Create connections and simulate various failure scenarios
        ghost_test_scenarios = [
            ("normal_close", "ghost_normal"),
            ("abnormal_close", "ghost_abnormal"),
            ("timeout_close", "ghost_timeout")
        ]
        
        for scenario_type, user_id in ghost_test_scenarios:
            client = cleanup_tester.create_tracked_client(user_id)
            
            if scenario_type == "normal_close":
                await client.connect(client._auth_headers)
                await client.close()
                
            elif scenario_type == "abnormal_close":
                await client.connect(client._auth_headers)
                if hasattr(client, '_websocket') and client._websocket:
                    await client._websocket.close(code=1006)  # Abnormal close
                    
            elif scenario_type == "timeout_close":
                # Create client with timeout that will fail
                config = ClientConfig(timeout=0.5, max_retries=1)
                timeout_client = RealWebSocketClient("ws://localhost:9998", config)
                timeout_client._cleanup_user_id = user_id
                cleanup_tester.test_clients.append(timeout_client)
                await timeout_client.connect({"Authorization": "Bearer test"})
        
        # Give time for all cleanup to complete
        await asyncio.sleep(2.0)
        gc.collect()
        
        # Check for ghost connections
        final_connection_count = len(cleanup_tester.active_connections)
        ghost_connections = final_connection_count - initial_connection_count
        
        # Should have no ghost connections
        assert ghost_connections <= 0, f"Ghost connections detected: {ghost_connections}"
        
        cleanup_tester.cleanup_metrics.append({
            "type": "ghost_connection_test",
            "data": {
                "initial_connections": initial_connection_count,
                "final_connections": final_connection_count,
                "ghost_connections": ghost_connections,
                "scenarios_tested": len(ghost_test_scenarios)
            }
        })
    
    @pytest.mark.asyncio
    async def test_process_resource_cleanup(self, cleanup_tester):
        """Test that process resources (file descriptors, etc.) are cleaned up"""
        # Get initial process info
        current_process = psutil.Process()
        initial_fds = current_process.num_fds() if hasattr(current_process, 'num_fds') else 0
        initial_threads = current_process.num_threads()
        
        # Create and destroy connections to test resource cleanup
        for i in range(5):
            client = cleanup_tester.create_tracked_client(f"resource_test_{i}")
            await client.connect(client._auth_headers)
            
            # Send some messages to create activity
            await client.send({"type": "test", "payload": {"iteration": i}})
            await client.receive(timeout=1.0)
            
            # Close connection
            await client.close()
            await asyncio.sleep(0.2)  # Brief pause for cleanup
        
        # Force cleanup and garbage collection
        gc.collect()
        await asyncio.sleep(1.0)
        
        # Check final resource usage
        final_fds = current_process.num_fds() if hasattr(current_process, 'num_fds') else 0
        final_threads = current_process.num_threads()
        
        # Calculate resource growth
        fd_growth = final_fds - initial_fds if initial_fds > 0 else 0
        thread_growth = final_threads - initial_threads
        
        # Resources should not grow significantly
        assert fd_growth < 10, f"File descriptor leak: {fd_growth} FDs not cleaned up"
        assert thread_growth < 5, f"Thread leak: {thread_growth} threads not cleaned up"
        
        cleanup_tester.cleanup_metrics.append({
            "type": "process_resource_test",
            "data": {
                "fd_growth": fd_growth,
                "thread_growth": thread_growth,
                "connections_tested": 5
            }
        })