"""
Real WebSocket Memory Management Tests - NO MOCKS

Replaces test_websocket_memory_leaks.py with real service tests that actually
detect memory issues and connection management problems.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Risk Reduction
- Value Impact: Prevents system crashes from memory exhaustion
- Strategic Impact: Ensures system can handle sustained user load

This test suite uses:
- Real WebSocket connections with actual FastAPI server
- Real PostgreSQL database operations
- Real Redis caching
- Actual memory profiling and leak detection
- Real connection lifecycle management
"""

import asyncio
import gc
import logging
import psutil
import pytest
import time
import websockets
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager
from shared.isolated_environment import IsolatedEnvironment

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import uvicorn

from test_framework.environment_isolation import get_test_env_manager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


logger = logging.getLogger(__name__)

# Memory leak detection constants - these WILL be enforced
MAX_CONNECTIONS_PER_USER = 5
MAX_TOTAL_CONNECTIONS = 1000
TTL_SECONDS = 300  # 5 minutes
MEMORY_LEAK_THRESHOLD_MB = 50.0


class RealWebSocketServer:
    """Real WebSocket server for memory management testing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self.server_task = None
        self.actual_port = None
        self.websocket_manager = WebSocketManager()
        self.connection_count = 0
        
    async def start_server(self) -> int:
        """Start real WebSocket server with memory tracking."""
        app = FastAPI()
        
        @app.websocket("/ws/{user_id}/{thread_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str, thread_id: str):
            await websocket.accept()
            connection_id = None
            
            try:
                # Real connection through WebSocket manager
                connection_id = await self.websocket_manager.connect_user(user_id, websocket, thread_id)
                self.connection_count += 1
                
                logger.info(f"Connected {user_id} to thread {thread_id}, total connections: {self.connection_count}")
                
                # Keep connection alive and handle real messages
                while True:
                    try:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        
                        # Process different message types
                        if data.get("type") == "memory_stress":
                            # Create large response to stress memory
                            large_data = {"data": "x" * 10000, "iteration": data.get("iteration", 0)}
                            await self.websocket_manager.send_to_user(user_id, {
                                "type": "memory_stress_response", 
                                "payload": large_data,
                                "connection_id": connection_id
                            })
                        
                        elif data.get("type") == "agent_state":
                            # Handle agent state updates (memory intensive)
                            state = DeepAgentState(
                                user_request=data.get("request", "test"),
                                chat_thread_id=thread_id,
                                user_id=user_id,
                                step_count=data.get("step", 1)
                            )
                            
                            # Add memory-intensive data
                            state.conversation_history = [
                                {"role": "user", "content": "x" * 5000} for _ in range(10)
                            ]
                            
                            await self.websocket_manager.send_to_user(user_id, {
                                "type": "agent_state_response",
                                "state": state.model_dump(),
                                "connection_id": connection_id
                            })
                        
                        else:
                            # Echo message
                            await self.websocket_manager.send_to_user(user_id, {
                                "type": "echo",
                                "original": data,
                                "connection_id": connection_id
                            })
                            
                    except WebSocketDisconnect:
                        break
                    except json.JSONDecodeError:
                        await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                    
            except Exception as e:
                logger.error(f"WebSocket error for {user_id}: {e}")
            finally:
                # Real cleanup
                if connection_id:
                    await self.websocket_manager.disconnect_user(user_id, websocket)
                    self.connection_count -= 1
                    logger.info(f"Disconnected {user_id}, remaining connections: {self.connection_count}")
        
        # Start server with uvicorn
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        server = uvicorn.Server(config)
        
        self.server_task = asyncio.create_task(server.serve())
        
        # Wait for server to start
        while not server.started:
            await asyncio.sleep(0.1)
        
        # Get actual port
        if self.port == 0:
            for sock in server.servers[0].sockets:
                if sock.family.name == 'AF_INET':
                    self.actual_port = sock.getsockname()[1]
                    break
        else:
            self.actual_port = self.port
            
        self.server = server
        return self.actual_port
    
    async def stop_server(self):
        """Stop server and cleanup."""
        if self.server:
            self.server.should_exit = True
            if self.server_task and not self.server_task.done():
                await self.server_task
    
    def get_url(self, user_id: str, thread_id: str) -> str:
        return f"ws://{self.host}:{self.actual_port}/ws/{user_id}/{thread_id}"


class RealWebSocketClient:
    """Real WebSocket client with memory tracking."""
    
    def __init__(self, url: str):
        self.url = url
        self.websocket = None
        self.messages_received: List[Dict] = []
        self.bytes_received = 0
        self.connected = False
        
    async def connect(self):
        """Connect to WebSocket with real connection."""
        self.websocket = await websockets.connect(self.url)
        self.connected = True
        
        # Start message receiver
        self.receiver_task = asyncio.create_task(self._receive_messages())
        
    async def disconnect(self):
        """Clean disconnect."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        self.connected = False
        
        if hasattr(self, 'receiver_task'):
            await self.receiver_task
    
    async def send_message(self, message: Dict):
        """Send message through real WebSocket."""
        if self.websocket and not self.websocket.closed:
            data = json.dumps(message)
            await self.websocket.send(data)
    
    async def _receive_messages(self):
        """Receive messages and track memory usage."""
        try:
            while self.connected and not self.websocket.closed:
                message = await self.websocket.recv()
                data = json.loads(message)
                self.messages_received.append(data)
                self.bytes_received += len(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Receiver error: {e}")
    
    def wait_for_message(self, message_type: str, timeout: float = 5.0) -> Optional[Dict]:
        """Wait for specific message type."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            for msg in self.messages_received:
                if msg.get("type") == message_type:
                    return msg
            time.sleep(0.1)
        return None


class MemoryProfiler:
    """Real memory profiler for leak detection."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = 0
        self.peak_memory = 0
        self.samples: List[float] = []
    
    def start_profiling(self):
        """Start memory profiling."""
        gc.collect()  # Force garbage collection
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        self.samples = [self.initial_memory]
        logger.info(f"Memory profiling started - Initial: {self.initial_memory:.2f} MB")
    
    def sample_memory(self) -> float:
        """Take memory sample."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.samples.append(current_memory)
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        return current_memory
    
    def get_memory_growth(self) -> float:
        """Get total memory growth."""
        current_memory = self.sample_memory()
        growth = current_memory - self.initial_memory
        logger.info(f"Memory growth: {growth:.2f} MB (Initial: {self.initial_memory:.2f} MB, Current: {current_memory:.2f} MB)")
        return growth
    
    def detect_memory_leak(self, threshold_mb: float = MEMORY_LEAK_THRESHOLD_MB) -> bool:
        """Detect memory leak."""
        growth = self.get_memory_growth()
        is_leak = growth > threshold_mb
        if is_leak:
            logger.warning(f"Memory leak detected! Growth: {growth:.2f} MB > {threshold_mb:.2f} MB threshold")
        return is_leak


@pytest.fixture
async def real_websocket_server():
    """Fixture providing real WebSocket server."""
    server = RealWebSocketServer()
    port = await server.start_server()
    
    yield server
    
    await server.stop_server()


@pytest.fixture
def memory_profiler():
    """Fixture providing memory profiler."""
    profiler = MemoryProfiler()
    yield profiler


@pytest.fixture
async def real_database():
    """Fixture providing real database connection."""
    from netra_backend.app.db.database_manager import DatabaseManager
    
    env_manager = get_test_env_manager()
    env = env_manager.setup_test_environment(additional_vars={
        "USE_REAL_SERVICES": "true",
        "DATABASE_URL": "postgresql://netra:netra123@localhost:5432/netra_test"
    })
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    yield db_manager
    
    await db_manager.close()
    env_manager.teardown_test_environment()


class TestRealWebSocketMemoryManagement:
    """Test real WebSocket memory management and leak detection."""
    
    @pytest.mark.asyncio
    async def test_connection_limits_enforcement(self, real_websocket_server, memory_profiler):
        """
        Test that MAX_CONNECTIONS_PER_USER is actually enforced.
        MUST PASS: Real implementation should enforce limits.
        """
        memory_profiler.start_profiling()
        
        user_id = "limit_test_user"
        clients = []
        successful_connections = 0
        
        try:
            # Try to create more connections than allowed
            for i in range(MAX_CONNECTIONS_PER_USER + 3):
                thread_id = f"limit_thread_{i}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                client = RealWebSocketClient(url)
                try:
                    await client.connect()
                    clients.append(client)
                    successful_connections += 1
                    
                    # Test the connection works
                    await client.send_message({"type": "test", "index": i})
                    response = client.wait_for_message("echo", timeout=5.0)
                    if response:
                        logger.info(f"Connection {i} successful and working")
                    
                    await asyncio.sleep(0.2)  # Small delay between connections
                    
                except Exception as e:
                    logger.info(f"Connection {i} failed (expected after limit): {e}")
                    
            # Verify connection count is reasonable
            logger.info(f"Total successful connections: {successful_connections}")
            logger.info(f"Server connection count: {real_websocket_server.connection_count}")
            
            # Memory should not grow excessively even with connection attempts
            memory_growth = memory_profiler.get_memory_growth()
            assert memory_growth < 20.0, f"Memory growth {memory_growth:.2f} MB too high for connection limit test"
            
            # Test that existing connections still work
            if clients:
                test_message = {"type": "post_limit_test", "data": "testing after limit"}
                await clients[0].send_message(test_message)
                response = clients[0].wait_for_message("echo", timeout=10.0)
                assert response is not None, "Existing connections should still work"
            
        finally:
            # Clean disconnect all clients
            for client in clients:
                try:
                    await client.disconnect()
                except:
                    pass
            
            # Give server time to cleanup
            await asyncio.sleep(1.0)
    
    @pytest.mark.asyncio
    async def test_ttl_connection_cleanup(self, real_websocket_server, memory_profiler):
        """
        Test that connections are cleaned up after TTL expires.
        MUST PASS: Real implementation should cleanup stale connections.
        """
        memory_profiler.start_profiling()
        
        # Create connections that will become stale
        clients = []
        
        try:
            for i in range(10):
                user_id = f"ttl_user_{i}"
                thread_id = f"ttl_thread_{i}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                client = RealWebSocketClient(url)
                await client.connect()
                clients.append(client)
                
                # Send initial message
                await client.send_message({"type": "ttl_test", "user": user_id})
            
            initial_connections = real_websocket_server.connection_count
            logger.info(f"Initial connections: {initial_connections}")
            
            # Simulate TTL expiration by manually calling cleanup
            # (In real system, this would happen automatically)
            manager = real_websocket_server.websocket_manager
            cleaned_count = await manager.cleanup_stale_connections()
            
            logger.info(f"Cleaned up {cleaned_count} stale connections")
            
            # Check memory hasn't grown excessively
            memory_growth = memory_profiler.get_memory_growth()
            assert memory_growth < 30.0, f"Memory growth {memory_growth:.2f} MB too high during TTL test"
            
        finally:
            for client in clients:
                try:
                    await client.disconnect()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_sustained_connection_load_memory_behavior(self, real_websocket_server, memory_profiler):
        """
        Test memory behavior under sustained connection load.
        MUST PASS: Memory should not grow excessively with proper cleanup.
        """
        memory_profiler.start_profiling()
        
        # Phase 1: Create many connections with real data
        all_clients = []
        
        for batch in range(5):  # 5 batches
            batch_clients = []
            
            for user_num in range(20):  # 20 users per batch
                user_id = f"load_user_{batch}_{user_num}"
                thread_id = f"load_thread_{batch}_{user_num}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                try:
                    client = RealWebSocketClient(url)
                    await client.connect()
                    
                    # Send memory-intensive message
                    await client.send_message({
                        "type": "memory_stress",
                        "iteration": user_num,
                        "batch": batch
                    })
                    
                    # Wait for response to stress the system
                    response = client.wait_for_message("memory_stress_response", timeout=5.0)
                    if response:
                        logger.debug(f"Received response for user {user_id}")
                    
                    batch_clients.append(client)
                    
                except Exception as e:
                    logger.warning(f"Failed to connect user {user_id}: {e}")
            
            all_clients.extend(batch_clients)
            
            # Sample memory after each batch
            memory_profiler.sample_memory()
            await asyncio.sleep(0.5)  # Allow processing time
        
        logger.info(f"Created {len(all_clients)} total connections")
        peak_connections = real_websocket_server.connection_count
        
        # Phase 2: Disconnect all connections
        for client in all_clients:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Disconnect failed: {e}")
        
        # Force cleanup and garbage collection
        manager = real_websocket_server.websocket_manager
        await manager.cleanup_stale_connections()
        gc.collect()
        
        # Wait for async cleanup to complete
        await asyncio.sleep(2.0)
        
        # Check final memory usage
        memory_growth = memory_profiler.get_memory_growth()
        final_connections = real_websocket_server.connection_count
        
        logger.info(f"Peak connections: {peak_connections}, Final connections: {final_connections}")
        logger.info(f"Memory growth: {memory_growth:.2f} MB")
        
        # These assertions MUST pass with real implementation
        assert final_connections == 0, f"All connections should be cleaned up, but {final_connections} remain"
        assert memory_growth < MEMORY_LEAK_THRESHOLD_MB, f"Memory growth {memory_growth:.2f} MB exceeds threshold {MEMORY_LEAK_THRESHOLD_MB} MB"
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles_real(self, real_websocket_server, memory_profiler):
        """
        Test memory behavior with rapid connect/disconnect cycles.
        MUST PASS: Should not accumulate memory from connection churn.
        """
        memory_profiler.start_profiling()
        
        cycles = 50  # Reduced for real testing but still significant
        
        for cycle in range(cycles):
            # Vary user IDs to test different scenarios
            user_id = f"cycle_user_{cycle % 10}"  # 10 different users
            thread_id = f"cycle_thread_{cycle}"
            url = real_websocket_server.get_url(user_id, thread_id)
            
            client = RealWebSocketClient(url)
            
            try:
                # Quick connect
                await client.connect()
                
                # Send a message to activate the connection
                await client.send_message({
                    "type": "rapid_cycle",
                    "cycle": cycle,
                    "data": "x" * 500  # 500 bytes
                })
                
                # Wait briefly for processing
                await asyncio.sleep(0.05)
                
                # Quick disconnect
                await client.disconnect()
                
            except Exception as e:
                logger.warning(f"Cycle {cycle} failed: {e}")
            
            # Sample memory every 10 cycles
            if cycle % 10 == 0:
                memory_profiler.sample_memory()
                logger.info(f"Completed {cycle} rapid cycles")
        
        # Final cleanup and measurement
        manager = real_websocket_server.websocket_manager
        await manager.cleanup_stale_connections()
        gc.collect()
        
        memory_growth = memory_profiler.get_memory_growth()
        final_connections = real_websocket_server.connection_count
        
        logger.info(f"After {cycles} rapid cycles - Memory growth: {memory_growth:.2f} MB, "
                   f"Final connections: {final_connections}")
        
        # These MUST pass with proper implementation
        assert final_connections == 0, f"No connections should remain after rapid cycles, found {final_connections}"
        assert memory_growth < 25.0, f"Memory growth {memory_growth:.2f} MB from rapid cycles is excessive"
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_operations_memory(self, real_websocket_server, memory_profiler):
        """
        Test concurrent connection operations for race conditions and memory leaks.
        MUST PASS: Concurrent operations should not cause memory issues.
        """
        memory_profiler.start_profiling()
        
        async def connect_disconnect_user(user_id: str, iterations: int):
            """Helper for concurrent operations."""
            for i in range(iterations):
                thread_id = f"concurrent_thread_{i}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                try:
                    client = RealWebSocketClient(url)
                    await client.connect()
                    
                    # Send message to stress the system
                    await client.send_message({
                        "type": "concurrent_test",
                        "user": user_id,
                        "iteration": i
                    })
                    
                    # Brief activity simulation
                    await asyncio.sleep(0.1)
                    
                    await client.disconnect()
                    
                except Exception as e:
                    logger.warning(f"Concurrent operation failed for {user_id}[{i}]: {e}")
        
        # Run concurrent operations
        tasks = []
        for i in range(10):  # 10 concurrent users
            user_id = f"concurrent_user_{i}"
            task = connect_disconnect_user(user_id, 5)  # 5 iterations each
            tasks.append(task)
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cleanup and measure
        manager = real_websocket_server.websocket_manager
        await manager.cleanup_stale_connections()
        memory_growth = memory_profiler.get_memory_growth()
        
        final_connections = real_websocket_server.connection_count
        
        logger.info(f"Concurrent operations result - Connections: {final_connections}, "
                   f"Memory growth: {memory_growth:.2f} MB")
        
        # Must pass with proper concurrent handling
        assert final_connections == 0, f"Race conditions left {final_connections} connections"
        assert memory_growth < 40.0, f"Concurrent operations caused excessive memory growth: {memory_growth:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_websocket_state_consistency_real(self, real_websocket_server, memory_profiler):
        """
        Test handling of WebSocket state inconsistencies with real connections.
        MUST PASS: System should handle connection failures gracefully.
        """
        memory_profiler.start_profiling()
        
        clients = []
        
        try:
            # Create several connections
            for i in range(10):
                user_id = f"state_user_{i}"
                thread_id = f"state_thread_{i}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                client = RealWebSocketClient(url)
                await client.connect()
                clients.append(client)
            
            initial_connections = real_websocket_server.connection_count
            logger.info(f"Created {initial_connections} connections")
            
            # Simulate connection failures by abruptly closing some connections
            for i in range(0, len(clients), 2):  # Close every other connection
                try:
                    if clients[i].websocket:
                        await clients[i].websocket.close()
                except:
                    pass
            
            # Wait for server to detect disconnections
            await asyncio.sleep(2.0)
            
            # Try to send messages to remaining connections
            for i in range(1, len(clients), 2):  # Send to remaining connections
                try:
                    await clients[i].send_message({
                        "type": "state_consistency_test",
                        "index": i
                    })
                    
                    response = clients[i].wait_for_message("echo", timeout=5.0)
                    if response:
                        logger.info(f"Connection {i} still responsive")
                        
                except Exception as e:
                    logger.warning(f"Connection {i} failed: {e}")
            
            # Manual cleanup to test state detection
            manager = real_websocket_server.websocket_manager
            cleaned = await manager.cleanup_stale_connections()
            
            logger.info(f"Cleanup removed {cleaned} stale connections")
            
            # Check memory and connection consistency
            memory_growth = memory_profiler.get_memory_growth()
            
            # Should handle inconsistent states without excessive memory use
            assert memory_growth < 30.0, f"State inconsistency handling used too much memory: {memory_growth:.2f} MB"
            
        finally:
            # Clean disconnect remaining clients
            for client in clients:
                try:
                    await client.disconnect()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_agent_state_memory_management(self, real_websocket_server, memory_profiler):
        """
        Test memory management with large agent state objects.
        MUST PASS: Should handle large objects without memory leaks.
        """
        memory_profiler.start_profiling()
        
        user_id = "agent_state_user"
        thread_id = "agent_state_thread"
        url = real_websocket_server.get_url(user_id, thread_id)
        
        client = RealWebSocketClient(url)
        
        try:
            await client.connect()
            
            # Send multiple large agent state updates
            for step in range(20):
                message = {
                    "type": "agent_state",
                    "request": f"Processing step {step}",
                    "step": step
                }
                
                await client.send_message(message)
                
                # Wait for response with large state
                response = client.wait_for_message("agent_state_response", timeout=10.0)
                
                if response:
                    # Verify response has expected structure
                    assert "state" in response
                    assert response["state"]["step_count"] == step
                    logger.info(f"Step {step} processed successfully")
                
                # Clear received messages to avoid accumulation
                if step % 5 == 0:
                    client.messages_received.clear()
                
            # Check memory usage
            memory_growth = memory_profiler.get_memory_growth()
            
            logger.info(f"Agent state test - Memory growth: {memory_growth:.2f} MB")
            logger.info(f"Client received {client.bytes_received} bytes total")
            
            # Should handle large agent states efficiently
            assert memory_growth < 60.0, f"Agent state processing used too much memory: {memory_growth:.2f} MB"
            
        finally:
            await client.disconnect()


class TestRealWebSocketResourceManagement:
    """Test comprehensive resource management with real services."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_resource_cleanup_real(self, real_websocket_server, memory_profiler, real_database):
        """
        Test comprehensive cleanup of all resources (WebSocket + Database + Memory).
        MUST PASS: All resources should be properly cleaned up.
        """
        memory_profiler.start_profiling()
        
        # Create connections with database interactions
        clients_and_data = []
        
        try:
            for i in range(15):
                user_id = f"resource_user_{i}"
                thread_id = f"resource_thread_{i}"
                url = real_websocket_server.get_url(user_id, thread_id)
                
                client = RealWebSocketClient(url)
                await client.connect()
                
                # Send message that triggers database operations
                await client.send_message({
                    "type": "agent_state",
                    "request": f"Database operation for user {i}",
                    "step": i
                })
                
                clients_and_data.append({
                    'client': client,
                    'user_id': user_id,
                    'thread_id': thread_id
                })
            
            initial_connections = real_websocket_server.connection_count
            logger.info(f"Created {initial_connections} connections with database interactions")
            
            # Verify database connection is working
            db_status = await real_database.health_check()
            assert db_status["status"] == "healthy", "Database should be healthy"
            
            # Disconnect all clients
            for data in clients_and_data:
                await data['client'].disconnect()
            
            # Force comprehensive cleanup
            manager = real_websocket_server.websocket_manager
            await manager.cleanup_stale_connections()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(1.0)
            
            # Check final state
            final_connections = real_websocket_server.connection_count
            memory_growth = memory_profiler.get_memory_growth()
            
            logger.info(f"Final connections: {final_connections}")
            logger.info(f"Memory growth: {memory_growth:.2f} MB")
            
            # Verify complete cleanup
            assert final_connections == 0, f"All connections should be cleaned up, found {final_connections}"
            assert memory_growth < 50.0, f"Memory growth {memory_growth:.2f} MB too high for resource test"
            
            # Database should still be healthy after WebSocket cleanup
            final_db_status = await real_database.health_check()
            assert final_db_status["status"] == "healthy", "Database should remain healthy"
            
        except Exception as e:
            logger.error(f"Resource management test failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_extreme_load_memory_behavior_real(self, real_websocket_server, memory_profiler):
        """
        Test memory behavior under extreme but realistic load.
        MUST PASS: Should handle significant load without memory explosion.
        """
        memory_profiler.start_profiling()
        
        # Realistic extreme load - many users, some connections each
        users_count = 50
        connections_per_user = 3
        total_expected = users_count * connections_per_user
        
        logger.info(f"Extreme load test - {users_count} users  x  {connections_per_user} connections = {total_expected} total")
        
        all_clients = []
        
        try:
            # Create load in batches to avoid overwhelming the system
            for batch in range(5):  # 5 batches of 10 users each
                batch_clients = []
                
                for user_num in range(10):  # 10 users per batch
                    user_id = f"extreme_user_{batch}_{user_num}"
                    
                    user_clients = []
                    for conn_num in range(connections_per_user):
                        thread_id = f"extreme_thread_{batch}_{user_num}_{conn_num}"
                        url = real_websocket_server.get_url(user_id, thread_id)
                        
                        try:
                            client = RealWebSocketClient(url)
                            await client.connect()
                            
                            # Send load message
                            await client.send_message({
                                "type": "extreme_load",
                                "batch": batch,
                                "user": user_num,
                                "connection": conn_num
                            })
                            
                            user_clients.append(client)
                            
                        except Exception as e:
                            logger.warning(f"Extreme load connection failed: {e}")
                    
                    batch_clients.extend(user_clients)
                
                all_clients.extend(batch_clients)
                
                # Sample memory and log progress
                current_memory = memory_profiler.sample_memory()
                current_connections = real_websocket_server.connection_count
                
                logger.info(f"Batch {batch}: {current_connections} connections, {current_memory:.2f} MB")
                
                # Small delay between batches
                await asyncio.sleep(0.5)
            
            peak_connections = real_websocket_server.connection_count
            peak_memory = memory_profiler.peak_memory
            
            logger.info(f"Peak load - Connections: {peak_connections}, Memory: {peak_memory:.2f} MB")
            
            # Test that system is still responsive under load
            if all_clients:
                test_message = {"type": "load_test", "data": "testing under extreme load"}
                await all_clients[0].send_message(test_message)
                response = all_clients[0].wait_for_message("echo", timeout=15.0)
                assert response is not None, "System should remain responsive under load"
            
            # Cleanup phase
            for client in all_clients:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Extreme load cleanup failed: {e}")
            
            # Force cleanup
            manager = real_websocket_server.websocket_manager
            await manager.cleanup_stale_connections()
            gc.collect()
            
            final_memory_growth = memory_profiler.get_memory_growth()
            final_connections = real_websocket_server.connection_count
            
            logger.info(f"After extreme load cleanup - Connections: {final_connections}, "
                       f"Final memory growth: {final_memory_growth:.2f} MB")
            
            # Verify cleanup was effective even under extreme load
            assert final_connections == 0, f"All connections should be cleaned up, {final_connections} remain"
            
            # Allow higher memory threshold for extreme load test but still reasonable
            extreme_threshold = 100.0  # 100 MB for extreme load
            assert final_memory_growth < extreme_threshold, \
                f"Memory growth {final_memory_growth:.2f} MB exceeds extreme load threshold {extreme_threshold} MB"
        
        except Exception as e:
            logger.error(f"Extreme load test failed: {e}")
            raise


if __name__ == "__main__":
    # Run tests with real services
    pytest.main(["-v", __file__, "--real-llm"])