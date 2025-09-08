"""
Integration tests for WebSocket Scalability and Load - Testing performance under concurrent load.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise
- Business Goal: Platform scalability and concurrent user support
- Value Impact: Ensures system handles multiple users simultaneously without degradation
- Strategic Impact: Critical for scaling business - validates infrastructure can handle growth

These integration tests validate WebSocket performance under concurrent load,
resource utilization, and scaling characteristics that support business growth.
"""

import pytest
import asyncio
import statistics
import time
from datetime import datetime, timezone
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.models import User


class TestWebSocketScalabilityLoadIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket scalability and load handling."""
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for load testing."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.fixture
    async def test_users(self, real_services_fixture):
        """Create multiple test users for load testing."""
        db = real_services_fixture["db"]
        users = []
        
        for i in range(50):  # Create 50 users for load testing
            user = User(
                email=f"load_test_user_{i}@example.com",
                name=f"Load Test User {i}",
                subscription_tier="enterprise" if i < 10 else "early"  # Mix of tiers
            )
            db.add(user)
            users.append(user)
        
        await db.commit()
        for user in users:
            await db.refresh(user)
        
        return users
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_connection_establishment(self, real_services_fixture, test_users,
                                                      websocket_manager, websocket_utility):
        """Test concurrent establishment of multiple WebSocket connections."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection establishment tasks
        connection_tasks = []
        expected_connections = []
        
        async def establish_connection(user, connection_id):
            """Helper to establish single connection."""
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=connection_id,
                user_id=str(user.id),
                websocket=websocket,
                metadata={
                    "load_test": True,
                    "user_tier": user.subscription_tier,
                    "established_at": datetime.now(timezone.utc).isoformat()
                }
            )
            await websocket_manager.add_connection(connection)
            return connection, websocket
        
        # Create concurrent connection tasks
        for i, user in enumerate(test_users[:20]):  # Test with 20 concurrent connections
            connection_id = f"load_test_conn_{i}"
            task = asyncio.create_task(establish_connection(user, connection_id))
            connection_tasks.append(task)
            expected_connections.append(connection_id)
        
        # Measure connection establishment time
        start_time = time.time()
        
        # Execute all connection establishments concurrently
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        establishment_time = time.time() - start_time
        
        # Verify connection establishment performance
        successful_connections = []
        failed_connections = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_connections.append(f"Connection {i} failed: {result}")
            else:
                connection, websocket = result
                successful_connections.append(connection)
        
        # Performance assertions
        assert len(successful_connections) >= 18, f"Should establish at least 18/20 connections, got {len(successful_connections)}"
        assert establishment_time < 5.0, f"Connection establishment took {establishment_time}s (too slow)"
        assert len(failed_connections) <= 2, f"Too many connection failures: {failed_connections}"
        
        # Verify connections are properly tracked
        active_connections = websocket_manager.get_all_connections()
        assert len(active_connections) >= len(successful_connections)
        
        # Test connection isolation
        connection_user_ids = {conn.user_id for conn in successful_connections}
        assert len(connection_user_ids) == len(successful_connections), "Connections should be isolated by user"
        
        # Cleanup
        cleanup_tasks = []
        for connection in successful_connections:
            cleanup_tasks.append(
                asyncio.create_task(websocket_manager.remove_connection(connection.connection_id))
            )
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_high_message_throughput_performance(self, real_services_fixture, test_users,
                                                      websocket_manager, websocket_utility):
        """Test high message throughput performance."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Setup connections for throughput test
        connections = []
        websockets = []
        
        for i, user in enumerate(test_users[:10]):  # 10 users for throughput test
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=f"throughput_conn_{i}",
                user_id=str(user.id),
                websocket=websocket,
                metadata={"throughput_test": True}
            )
            await websocket_manager.add_connection(connection)
            connections.append(connection)
            websockets.append(websocket)
        
        # Generate high volume of messages
        message_count_per_user = 100
        total_messages = len(connections) * message_count_per_user
        
        async def send_user_messages(user_index, connection, websocket):
            """Send messages from one user."""
            user = test_users[user_index]
            messages_sent = 0
            
            for i in range(message_count_per_user):
                message = WebSocketMessage(
                    message_type=MessageType.USER_MESSAGE,
                    payload={
                        "content": f"High throughput message {i} from user {user_index}",
                        "sequence": i,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id=str(user.id)
                )
                
                try:
                    await websocket_manager.handle_message(
                        user_id=str(user.id),
                        websocket=websocket,
                        message=message
                    )
                    messages_sent += 1
                except Exception as e:
                    print(f"Message failed for user {user_index}: {e}")
                
                # Small delay to avoid overwhelming system
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            return messages_sent
        
        # Execute high throughput test
        start_time = time.time()
        
        throughput_tasks = []
        for i, (connection, websocket) in enumerate(zip(connections, websockets)):
            task = asyncio.create_task(send_user_messages(i, connection, websocket))
            throughput_tasks.append(task)
        
        # Wait for all message sending to complete
        messages_sent_results = await asyncio.gather(*throughput_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze throughput performance
        successful_sends = []
        for result in messages_sent_results:
            if isinstance(result, Exception):
                print(f"Throughput task failed: {result}")
            else:
                successful_sends.append(result)
        
        total_successful_messages = sum(successful_sends)
        messages_per_second = total_successful_messages / total_time
        
        # Performance assertions
        assert total_successful_messages >= total_messages * 0.9, f"Should send at least 90% of messages, sent {total_successful_messages}/{total_messages}"
        assert messages_per_second >= 50, f"Should handle at least 50 messages/second, achieved {messages_per_second:.1f}"
        assert total_time < 30, f"Throughput test took {total_time}s (too slow)"
        
        # Verify message delivery
        total_delivered = sum(len(ws.sent_messages) for ws in websockets)
        assert total_delivered >= total_successful_messages * 0.8, "Should deliver most sent messages"
        
        # Check for message ordering within each user
        for i, websocket in enumerate(websockets):
            user_messages = websocket.sent_messages
            if len(user_messages) > 1:
                # Verify some level of ordering (not all messages may be delivered)
                sequences = []
                for msg in user_messages:
                    if hasattr(msg, 'payload') and 'sequence' in msg.payload:
                        sequences.append(msg.payload['sequence'])
                
                if len(sequences) >= 2:
                    # Should have some ordering preservation
                    ordering_violations = sum(1 for i in range(1, len(sequences)) if sequences[i] < sequences[i-1])
                    assert ordering_violations < len(sequences) * 0.1, "Should maintain reasonable message ordering"
        
        # Cleanup
        cleanup_tasks = [websocket_manager.remove_connection(conn.connection_id) for conn in connections]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_memory_usage_under_load(self, real_services_fixture, test_users,
                                          websocket_manager, websocket_utility):
        """Test memory usage patterns under load."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Monitor memory usage during load test
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many connections with message history
        connections = []
        websockets = []
        
        for i, user in enumerate(test_users[:25]):  # 25 users with message history
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=f"memory_test_conn_{i}",
                user_id=str(user.id),
                websocket=websocket,
                metadata={
                    "memory_test": True,
                    "message_buffer_size": 100  # Buffer messages for each user
                }
            )
            await websocket_manager.add_connection(connection)
            connections.append(connection)
            websockets.append(websocket)
        
        connection_memory = process.memory_info().rss / 1024 / 1024
        
        # Send messages to build up memory usage
        for round_num in range(5):  # 5 rounds of messages
            message_tasks = []
            
            for i, (connection, websocket) in enumerate(zip(connections, websockets)):
                user = test_users[i]
                
                # Send batch of messages
                for msg_num in range(20):  # 20 messages per user per round
                    message = WebSocketMessage(
                        message_type=MessageType.AGENT_COMPLETED,
                        payload={
                            "agent_result": {
                                "analysis": f"Memory test analysis {round_num}-{msg_num}. " * 50,  # Larger payload
                                "data": [f"data_point_{j}" for j in range(100)],  # Array data
                                "metadata": {"round": round_num, "message": msg_num}
                            }
                        },
                        user_id=str(user.id)
                    )
                    
                    task = asyncio.create_task(
                        websocket_manager.send_to_user(str(user.id), message)
                    )
                    message_tasks.append(task)
            
            # Execute batch
            await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Check memory after each round
            current_memory = process.memory_info().rss / 1024 / 1024
            print(f"Memory after round {round_num}: {current_memory:.1f} MB")
            
            # Small delay between rounds
            await asyncio.sleep(0.1)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Memory usage assertions
        memory_increase = final_memory - initial_memory
        memory_per_connection = memory_increase / len(connections) if connections else 0
        
        print(f"Memory usage: Initial={initial_memory:.1f}MB, Final={final_memory:.1f}MB, Increase={memory_increase:.1f}MB")
        print(f"Memory per connection: {memory_per_connection:.2f}MB")
        
        # Memory should not grow excessively
        assert memory_increase < 500, f"Memory increase of {memory_increase:.1f}MB is too high"
        assert memory_per_connection < 5, f"Memory per connection of {memory_per_connection:.2f}MB is too high"
        
        # Test memory cleanup after connection removal
        cleanup_tasks = [websocket_manager.remove_connection(conn.connection_id) for conn in connections[:10]]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Allow garbage collection
        await asyncio.sleep(0.5)
        
        post_cleanup_memory = process.memory_info().rss / 1024 / 1024
        memory_freed = final_memory - post_cleanup_memory
        
        # Should free some memory after cleanup
        assert memory_freed >= 0, "Should not increase memory after cleanup"
        print(f"Memory freed after cleanup: {memory_freed:.1f}MB")
        
        # Cleanup remaining connections
        remaining_cleanup = [websocket_manager.remove_connection(conn.connection_id) for conn in connections[10:]]
        await asyncio.gather(*remaining_cleanup, return_exceptions=True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_limits_and_queueing(self, real_services_fixture, test_users,
                                                      websocket_manager, websocket_utility):
        """Test connection pool limits and queueing behavior."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Test connection limits (simulate reaching capacity)
        max_test_connections = 30
        connections = []
        connection_results = []
        
        async def attempt_connection(user_index):
            """Attempt to establish connection."""
            try:
                user = test_users[user_index % len(test_users)]
                websocket = await websocket_utility.create_mock_websocket()
                
                connection = await websocket_manager.create_connection(
                    connection_id=f"pool_test_conn_{user_index}",
                    user_id=str(user.id),
                    websocket=websocket,
                    metadata={
                        "pool_test": True,
                        "attempt_order": user_index
                    }
                )
                
                await websocket_manager.add_connection(connection)
                return {"success": True, "connection": connection, "index": user_index}
                
            except Exception as e:
                return {"success": False, "error": str(e), "index": user_index}
        
        # Attempt many concurrent connections
        connection_tasks = []
        for i in range(max_test_connections):
            task = asyncio.create_task(attempt_connection(i))
            connection_tasks.append(task)
        
        # Execute connection attempts
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze connection results
        successful_connections = []
        failed_connections = []
        exceptions = []
        
        for result in results:
            if isinstance(result, Exception):
                exceptions.append(result)
            elif result["success"]:
                successful_connections.append(result["connection"])
            else:
                failed_connections.append(result)
        
        # Verify connection limits are enforced gracefully
        total_successful = len(successful_connections)
        total_failed = len(failed_connections)
        
        print(f"Connection results: {total_successful} successful, {total_failed} failed, {len(exceptions)} exceptions")
        
        # Should successfully handle most connections
        assert total_successful >= max_test_connections * 0.7, f"Should handle at least 70% of connections, got {total_successful}/{max_test_connections}"
        
        # If there are failures, they should be graceful (not exceptions)
        assert len(exceptions) <= max_test_connections * 0.1, f"Too many connection exceptions: {len(exceptions)}"
        
        # Test that established connections work properly
        if successful_connections:
            # Test random sampling of connections
            test_sample = successful_connections[::5]  # Every 5th connection
            
            for i, connection in enumerate(test_sample):
                test_message = WebSocketMessage(
                    message_type=MessageType.SYSTEM_STATUS,
                    payload={"status": f"Testing connection {i}"},
                    user_id=connection.user_id
                )
                
                try:
                    await websocket_manager.send_to_user(
                        user_id=connection.user_id,
                        message=test_message
                    )
                except Exception as e:
                    print(f"Message failed for connection {connection.connection_id}: {e}")
        
        # Test connection replacement (remove some, add new ones)
        if len(successful_connections) > 10:
            # Remove 10 connections
            remove_tasks = []
            connections_to_remove = successful_connections[:10]
            
            for connection in connections_to_remove:
                remove_tasks.append(
                    asyncio.create_task(websocket_manager.remove_connection(connection.connection_id))
                )
            
            await asyncio.gather(*remove_tasks, return_exceptions=True)
            
            # Try to add new connections (should succeed after removal)
            new_connection_tasks = []
            for i in range(5):
                task = asyncio.create_task(attempt_connection(max_test_connections + i))
                new_connection_tasks.append(task)
            
            new_results = await asyncio.gather(*new_connection_tasks, return_exceptions=True)
            
            new_successful = sum(1 for r in new_results if isinstance(r, dict) and r.get("success"))
            assert new_successful >= 3, f"Should add new connections after removal, got {new_successful}/5"
        
        # Cleanup all remaining connections
        final_cleanup_tasks = []
        all_connections = websocket_manager.get_all_connections()
        
        for connection in all_connections:
            if "pool_test" in connection.metadata.get("pool_test", ""):
                final_cleanup_tasks.append(
                    asyncio.create_task(websocket_manager.remove_connection(connection.connection_id))
                )
        
        if final_cleanup_tasks:
            await asyncio.gather(*final_cleanup_tasks, return_exceptions=True)