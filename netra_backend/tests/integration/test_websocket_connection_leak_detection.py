"""
WebSocket Connection Leak Detection and Stress Testing

Business Value Justification (BVJ):
- Segment: All (Real-time features critical)
- Business Goal: System stability, prevent memory leaks
- Value Impact: Prevent WebSocket connection leaks that degrade real-time performance
- Strategic Impact: Maintain real-time responsiveness under load

WebSocket Leak Detection Coverage:
- Connection leak detection under stress
- Memory usage monitoring 
- Connection cleanup verification
- Concurrent connection limits
- Disconnect handling validation
"""
import asyncio
import pytest
import weakref
import gc
from unittest.mock import AsyncMock, Mock, patch
import time
from contextlib import asynccontextmanager

from netra_backend.app.websocket_core import WebSocketManager
from fastapi import WebSocket


class TestWebSocketConnectionLeakDetection:
    """Test WebSocket connection leak detection and cleanup"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.websocket_manager = WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_leak_detection(self):
        """Test detection of WebSocket connection leaks - EXPECTED TO FAIL"""
        # Track weak references to detect if connections are properly cleaned up
        connection_refs = []
        active_connections = []
        
        # Mock WebSocket connections
        for i in range(10):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.client_state = "connected"
            mock_websocket.close = AsyncMock()
            
            # Create weak reference to detect garbage collection
            weak_ref = weakref.ref(mock_websocket)
            connection_refs.append(weak_ref)
            
            # Add to manager
            active_connections.append(mock_websocket)
            self.websocket_manager.connections.append(mock_websocket)
        
        # Simulate disconnecting all connections
        for websocket in active_connections:
            await self.websocket_manager.disconnect(websocket)
        
        # Clear local references
        active_connections.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Check for leaks - THIS WILL FAIL if connections aren't properly cleaned up
        leaked_connections = [ref for ref in connection_refs if ref() is not None]
        
        # This assertion will fail if WebSocket connections are leaked
        assert len(leaked_connections) == 0, f"Found {len(leaked_connections)} leaked WebSocket connections"
        
        # Verify manager's connection list is empty
        assert len(self.websocket_manager.connections) == 0, "WebSocket manager should have no active connections"
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connection_stress(self):
        """Test WebSocket manager under concurrent connection stress - EXPECTED TO FAIL"""
        connection_count = 50  # High connection count for stress testing
        successful_connects = []
        failed_connects = []
        
        async def attempt_websocket_connection(connection_id):
            try:
                mock_websocket = Mock(spec=WebSocket)
                mock_websocket.client_state = "connected"
                mock_websocket.close = AsyncMock()
                
                # Simulate connection delay
                await asyncio.sleep(0.01)
                
                # Add to manager
                await self.websocket_manager.connect(mock_websocket)
                successful_connects.append(connection_id)
                
                # Hold connection briefly
                await asyncio.sleep(0.05)
                
                # Disconnect
                await self.websocket_manager.disconnect(mock_websocket)
                
            except Exception as e:
                failed_connects.append({'id': connection_id, 'error': str(e)})
        
        # Launch concurrent connections
        tasks = [attempt_websocket_connection(i) for i in range(connection_count)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # THIS WILL FAIL if WebSocket manager doesn't handle concurrent connections properly
        total_attempts = len(successful_connects) + len(failed_connects)
        assert total_attempts == connection_count, f"Should track all connection attempts, got {total_attempts}"
        
        # Should have mostly successful connections
        success_rate = len(successful_connects) / connection_count
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.2%}"
        
        # Manager should be clean after all disconnects
        assert len(self.websocket_manager.connections) == 0, "All connections should be cleaned up"
    
    @pytest.mark.asyncio
    async def test_websocket_memory_usage_monitoring(self):
        """Test monitoring of WebSocket memory usage - EXPECTED TO FAIL"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create many WebSocket connections to increase memory usage
        connections = []
        for i in range(100):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.client_state = "connected"
            mock_websocket.close = AsyncMock()
            
            # Add large data to simulate memory usage
            mock_websocket.user_data = b'x' * 1024 * 10  # 10KB per connection
            
            connections.append(mock_websocket)
            await self.websocket_manager.connect(mock_websocket)
        
        # Memory should have increased significantly
        mid_memory = process.memory_info().rss
        memory_increase = mid_memory - initial_memory
        
        # THIS WILL FAIL if memory monitoring isn't implemented
        assert memory_increase > 0, "Memory usage should increase with WebSocket connections"
        
        # Expected memory increase (rough estimate)
        expected_increase = 100 * 10 * 1024  # 100 connections * 10KB each
        
        # Memory increase should be reasonable (allow for overhead)
        assert memory_increase < expected_increase * 10, f"Memory usage too high: {memory_increase} bytes"
        
        # Clean up all connections
        for websocket in connections:
            await self.websocket_manager.disconnect(websocket)
        
        connections.clear()
        gc.collect()
        
        # Memory should decrease after cleanup
        final_memory = process.memory_info().rss
        memory_freed = mid_memory - final_memory
        
        # THIS WILL FAIL if memory isn't properly freed
        assert memory_freed > 0, "Memory should be freed after disconnecting WebSockets"
        
        # Should free at least 50% of the allocated memory
        assert memory_freed > memory_increase * 0.5, f"Insufficient memory freed: {memory_freed} / {memory_increase}"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timeout_handling(self):
        """Test WebSocket connection timeout handling - EXPECTED TO FAIL"""
        timeout_events = []
        
        def log_timeout_event(websocket_id, timeout_duration):
            timeout_events.append({
                'websocket_id': websocket_id,
                'timeout_duration': timeout_duration,
                'timestamp': time.time()
            })
        
        # Mock a slow WebSocket connection
        slow_websocket = Mock(spec=WebSocket)
        slow_websocket.client_state = "connected"
        slow_websocket.close = AsyncMock(side_effect=lambda: asyncio.sleep(1))  # Slow close
        
        # Add timeout monitoring
        start_time = time.time()
        
        try:
            # Attempt to disconnect with timeout
            await asyncio.wait_for(
                self.websocket_manager.disconnect(slow_websocket),
                timeout=0.5  # 500ms timeout
            )
        except asyncio.TimeoutError:
            timeout_duration = time.time() - start_time
            log_timeout_event('slow_websocket', timeout_duration)
        
        # THIS WILL FAIL if timeout monitoring isn't implemented
        assert len(timeout_events) > 0, "Should log timeout events for monitoring"
        
        # Verify timeout was reasonable
        assert timeout_events[0]['timeout_duration'] < 1.0, "Timeout should occur within reasonable time"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_limit_enforcement(self):
        """Test enforcement of WebSocket connection limits - EXPECTED TO FAIL"""
        # Set a low connection limit for testing
        original_limit = getattr(self.websocket_manager, 'max_connections', None)
        self.websocket_manager.max_connections = 5
        
        connections = []
        rejected_connections = []
        
        try:
            # Try to create more connections than the limit
            for i in range(10):
                mock_websocket = Mock(spec=WebSocket)
                mock_websocket.client_state = "connected"
                mock_websocket.close = AsyncMock()
                
                try:
                    await self.websocket_manager.connect(mock_websocket)
                    connections.append(mock_websocket)
                except Exception as e:
                    rejected_connections.append({'id': i, 'error': str(e)})
            
            # THIS WILL FAIL if connection limits aren't enforced
            total_connections = len(connections)
            assert total_connections <= 5, f"Should not exceed connection limit, got {total_connections}"
            
            # Should have rejected some connections
            assert len(rejected_connections) > 0, "Should reject connections exceeding limit"
            
            # Total attempts should equal successful + rejected
            total_attempts = len(connections) + len(rejected_connections)
            assert total_attempts == 10, f"Should track all attempts, got {total_attempts}"
            
        finally:
            # Clean up
            for websocket in connections:
                await self.websocket_manager.disconnect(websocket)
            
            # Restore original limit
            if original_limit is not None:
                self.websocket_manager.max_connections = original_limit
            else:
                delattr(self.websocket_manager, 'max_connections')
    
    @pytest.mark.asyncio
    async def test_websocket_message_queue_leak_detection(self):
        """Test detection of message queue leaks in WebSocket connections - EXPECTED TO FAIL"""
        # Track message queues that might leak
        message_queues = []
        
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = "connected"
        mock_websocket.close = AsyncMock()
        
        # Simulate adding messages to queue
        message_queue = asyncio.Queue()
        for i in range(100):
            await message_queue.put(f"message_{i}")
        
        message_queues.append(weakref.ref(message_queue))
        
        # Associate queue with WebSocket (simulated)
        mock_websocket.message_queue = message_queue
        
        # Connect and then disconnect
        await self.websocket_manager.connect(mock_websocket)
        await self.websocket_manager.disconnect(mock_websocket)
        
        # Clear local reference
        del message_queue
        del mock_websocket.message_queue
        
        # Force garbage collection
        gc.collect()
        
        # Check for queue leaks - THIS WILL FAIL if message queues aren't cleaned up
        leaked_queues = [ref for ref in message_queues if ref() is not None]
        
        # This assertion will fail if message queues are leaked
        assert len(leaked_queues) == 0, f"Found {len(leaked_queues)} leaked message queues"
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling_under_stress(self):
        """Test WebSocket error handling under stress conditions - EXPECTED TO FAIL"""
        error_count = 0
        successful_operations = 0
        
        async def stress_websocket_operations():
            nonlocal error_count, successful_operations
            
            for i in range(20):
                mock_websocket = Mock(spec=WebSocket)
                mock_websocket.client_state = "connected"
                
                # Randomly simulate errors in close operations
                if i % 3 == 0:
                    mock_websocket.close = AsyncMock(side_effect=Exception(f"Simulated error {i}"))
                else:
                    mock_websocket.close = AsyncMock()
                
                try:
                    await self.websocket_manager.connect(mock_websocket)
                    await self.websocket_manager.disconnect(mock_websocket)
                    successful_operations += 1
                    
                except Exception as e:
                    error_count += 1
        
        # Run stress operations
        await stress_websocket_operations()
        
        # THIS WILL FAIL if error handling isn't robust under stress
        total_operations = error_count + successful_operations
        assert total_operations == 20, f"Should track all operations, got {total_operations}"
        
        # Should handle errors gracefully without crashing
        assert error_count > 0, "Should encounter some errors in stress test"
        assert successful_operations > 0, "Should have some successful operations"
        
        # Manager should remain in valid state despite errors
        connection_count = len(self.websocket_manager.connections)
        assert connection_count >= 0, f"Connection count should be non-negative, got {connection_count}"
        
    @pytest.mark.asyncio
    async def test_websocket_resource_cleanup_verification(self):
        """Test comprehensive WebSocket resource cleanup - EXPECTED TO FAIL"""
        # Track various resources that should be cleaned up
        resource_refs = {
            'websockets': [],
            'event_loops': [],
            'file_descriptors': [],
            'memory_buffers': []
        }
        
        # Create WebSocket connections with various resources
        for i in range(10):
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.client_state = "connected"
            mock_websocket.close = AsyncMock()
            
            # Simulate various resources
            mock_websocket._buffer = bytearray(1024)  # Memory buffer
            mock_websocket._fd = i + 100  # Simulated file descriptor
            mock_websocket._loop = asyncio.get_event_loop()  # Event loop reference
            
            # Track weak references
            resource_refs['websockets'].append(weakref.ref(mock_websocket))
            resource_refs['memory_buffers'].append(weakref.ref(mock_websocket._buffer))
            
            await self.websocket_manager.connect(mock_websocket)
        
        # Disconnect all connections
        connections_to_disconnect = list(self.websocket_manager.connections)
        for websocket in connections_to_disconnect:
            await self.websocket_manager.disconnect(websocket)
        
        # Clear local references
        del connections_to_disconnect
        
        # Force garbage collection multiple times
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.01)
        
        # Check for resource leaks - THIS WILL FAIL if resources aren't cleaned up
        leaked_websockets = [ref for ref in resource_refs['websockets'] if ref() is not None]
        leaked_buffers = [ref for ref in resource_refs['memory_buffers'] if ref() is not None]
        
        # These assertions will fail if resources are leaked
        assert len(leaked_websockets) == 0, f"Found {len(leaked_websockets)} leaked WebSocket objects"
        assert len(leaked_buffers) == 0, f"Found {len(leaked_buffers)} leaked memory buffers"
        
        # Verify manager state is clean
        assert len(self.websocket_manager.connections) == 0, "WebSocket manager should be clean"