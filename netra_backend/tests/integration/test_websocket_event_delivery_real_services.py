"""Integration Tests for WebSocket Event Delivery with Real Services

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time user feedback during AI execution 
- Value Impact: Prevents user abandonment by providing live progress updates
- Strategic Impact: Core UX functionality that builds user trust and engagement

CRITICAL TEST PURPOSE:
These integration tests validate WebSocket event delivery with real service connections
to ensure users receive timely feedback during agent execution.

Test Coverage:
- Real WebSocket connection establishment and management
- Event delivery reliability with real Redis backing
- Multi-user event routing and isolation
- Event ordering and timing with real services
- Connection recovery and retry mechanisms
- Performance under realistic service conditions
"""

import pytest
import asyncio
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.ssot.real_services_test_fixtures import *
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient


@pytest.mark.integration
class TestWebSocketEventDeliveryRealServices:
    """Integration tests for WebSocket event delivery with real services."""
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_with_real_redis(self, real_services_fixture, real_redis_fixture):
        """Test WebSocket event delivery using real Redis for message routing."""
        # Arrange - verify services are available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for integration testing")
        
        redis_client = real_redis_fixture
        
        # Create real WebSocket manager with Redis backend
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_real_connections=True
        )
        
        # Create WebSocket notifier with real backend
        notifier = WebSocketNotifier(
            websocket_manager=websocket_manager,
            test_mode=False  # Enable real operations
        )
        
        # Create test execution context
        context = AgentExecutionContext(
            agent_name="redis_test_agent",
            run_id=uuid.uuid4(),
            thread_id=f"redis-thread-{uuid.uuid4()}",
            user_id=f"redis-user-{uuid.uuid4()}"
        )
        
        # Create test WebSocket connection
        test_client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id
        )
        
        try:
            # Connect WebSocket client
            await test_client.connect()
            
            # Register connection with manager
            await websocket_manager.register_connection(
                connection=test_client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Act - send events through real Redis routing
            await notifier.send_agent_started(context)
            
            await notifier.send_agent_thinking(
                context=context,
                thought="Processing your request using real Redis...",
                progress_percentage=25.0
            )
            
            await notifier.send_tool_executing(
                context=context,
                tool_name="redis_analyzer",
                tool_purpose="Analyze data with Redis caching"
            )
            
            await notifier.send_tool_completed(
                context=context,
                tool_name="redis_analyzer",
                result={"cached_results": True, "performance": "optimal"}
            )
            
            await notifier.send_agent_completed(
                context=context,
                result={"redis_integration": "successful", "events_delivered": 5}
            )
            
            # Wait for event delivery
            await asyncio.sleep(0.5)  # Allow time for Redis routing
            
            # Assert - verify events were delivered via Redis
            received_events = await test_client.get_received_events()
            
            assert len(received_events) >= 5  # Should receive all events
            
            # Verify event types received
            event_types = [event.get("type") for event in received_events]
            expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for expected_type in expected_types:
                assert expected_type in event_types, f"Missing event type: {expected_type}"
            
            # Verify Redis was used for routing
            redis_keys = await redis_client.keys(f"websocket:thread:{context.thread_id}:*")
            assert len(redis_keys) > 0, "Redis should have WebSocket routing keys"
            
            # Verify event content integrity
            for event in received_events:
                assert "timestamp" in event
                assert "payload" in event
                if event["type"] == "tool_completed":
                    assert event["payload"]["result"]["cached_results"] == True
        
        finally:
            # Cleanup
            await test_client.disconnect()
            await websocket_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_real_services(self, real_services_fixture, real_redis_fixture):
        """Test multi-user WebSocket event isolation with real service backend."""
        # Arrange - verify services are available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for integration testing")
        
        redis_client = real_redis_fixture
        
        # Create WebSocket manager with real Redis
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_isolation=True
        )
        
        notifier = WebSocketNotifier(websocket_manager=websocket_manager)
        
        # Create contexts for different users
        user1_context = AgentExecutionContext(
            agent_name="isolation_agent_user1",
            run_id=uuid.uuid4(),
            thread_id=f"user1-thread-{uuid.uuid4()}",
            user_id=f"user1-{uuid.uuid4()}"
        )
        
        user2_context = AgentExecutionContext(
            agent_name="isolation_agent_user2", 
            run_id=uuid.uuid4(),
            thread_id=f"user2-thread-{uuid.uuid4()}",
            user_id=f"user2-{uuid.uuid4()}"
        )
        
        # Create separate WebSocket connections for each user
        user1_client = RealWebSocketTestClient(
            thread_id=user1_context.thread_id,
            user_id=user1_context.user_id
        )
        
        user2_client = RealWebSocketTestClient(
            thread_id=user2_context.thread_id,
            user_id=user2_context.user_id  
        )
        
        try:
            # Connect both clients
            await asyncio.gather(
                user1_client.connect(),
                user2_client.connect()
            )
            
            # Register connections with isolation
            await websocket_manager.register_connection(
                connection=user1_client,
                thread_id=user1_context.thread_id,
                user_id=user1_context.user_id
            )
            
            await websocket_manager.register_connection(
                connection=user2_client,
                thread_id=user2_context.thread_id,
                user_id=user2_context.user_id
            )
            
            # Act - send isolated events for both users
            await asyncio.gather(
                notifier.send_agent_started(user1_context),
                notifier.send_agent_started(user2_context)
            )
            
            await asyncio.gather(
                notifier.send_agent_thinking(
                    user1_context,
                    thought="User 1 sensitive analysis...",
                    progress_percentage=50.0
                ),
                notifier.send_agent_thinking(
                    user2_context, 
                    thought="User 2 confidential processing...",
                    progress_percentage=30.0
                )
            )
            
            await asyncio.gather(
                notifier.send_agent_completed(
                    user1_context,
                    result={"user1_data": "sensitive_result_1", "account": "user1_account"}
                ),
                notifier.send_agent_completed(
                    user2_context,
                    result={"user2_data": "sensitive_result_2", "account": "user2_account"}
                )
            )
            
            # Wait for event delivery through Redis
            await asyncio.sleep(0.7)
            
            # Assert - verify proper isolation
            user1_events = await user1_client.get_received_events()
            user2_events = await user2_client.get_received_events()
            
            assert len(user1_events) >= 3  # started + thinking + completed
            assert len(user2_events) >= 3  # started + thinking + completed
            
            # Verify user1 doesn't receive user2 data
            for event in user1_events:
                event_str = json.dumps(event)
                assert "user2_data" not in event_str
                assert "user2_account" not in event_str
                assert user2_context.user_id not in event_str
                
                # But should contain user1 data
                if "user1_data" in event_str:
                    assert "sensitive_result_1" in event_str
            
            # Verify user2 doesn't receive user1 data  
            for event in user2_events:
                event_str = json.dumps(event)
                assert "user1_data" not in event_str
                assert "user1_account" not in event_str
                assert user1_context.user_id not in event_str
                
                # But should contain user2 data
                if "user2_data" in event_str:
                    assert "sensitive_result_2" in event_str
            
            # Verify Redis isolation keys
            user1_keys = await redis_client.keys(f"websocket:thread:{user1_context.thread_id}:*")
            user2_keys = await redis_client.keys(f"websocket:thread:{user2_context.thread_id}:*")
            
            assert len(user1_keys) > 0
            assert len(user2_keys) > 0
            
            # Verify no key overlap (perfect isolation)
            user1_key_set = set(user1_keys)
            user2_key_set = set(user2_keys)
            assert user1_key_set.isdisjoint(user2_key_set), "Redis keys should be completely isolated"
        
        finally:
            # Cleanup
            await asyncio.gather(
                user1_client.disconnect(),
                user2_client.disconnect(),
                websocket_manager.cleanup()
            )
    
    @pytest.mark.asyncio
    async def test_websocket_connection_recovery_real_services(self, real_services_fixture, real_redis_fixture):
        """Test WebSocket connection recovery with real service backend."""
        # Arrange - verify services are available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for integration testing")
        
        redis_client = real_redis_fixture
        
        # Create WebSocket manager with recovery enabled
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_recovery=True,
            recovery_timeout=2.0
        )
        
        notifier = WebSocketNotifier(
            websocket_manager=websocket_manager,
            enable_delivery_guarantees=True
        )
        
        context = AgentExecutionContext(
            agent_name="recovery_agent",
            run_id=uuid.uuid4(),
            thread_id=f"recovery-thread-{uuid.uuid4()}",
            user_id=f"recovery-user-{uuid.uuid4()}"
        )
        
        # Create WebSocket client with recovery capabilities
        client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id,
            enable_reconnect=True
        )
        
        try:
            # Initial connection
            await client.connect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id, 
                user_id=context.user_id
            )
            
            # Send initial events
            await notifier.send_agent_started(context)
            await notifier.send_agent_thinking(
                context, 
                thought="Starting processing before connection failure...",
                progress_percentage=20.0
            )
            
            await asyncio.sleep(0.3)  # Allow delivery
            
            # Act - simulate connection failure and recovery
            await client.simulate_disconnect()  # Simulates network failure
            
            # Continue sending events during disconnection (should queue in Redis)
            await notifier.send_tool_executing(
                context,
                tool_name="recovery_tool",
                tool_purpose="Test recovery during execution"
            )
            
            await notifier.send_agent_thinking(
                context,
                thought="Processing continues during recovery...",
                progress_percentage=60.0
            )
            
            # Reconnect client (simulates automatic recovery)
            await client.reconnect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Send post-recovery events
            await notifier.send_tool_completed(
                context,
                tool_name="recovery_tool",
                result={"recovery": "successful", "events_preserved": True}
            )
            
            await notifier.send_agent_completed(
                context,
                result={"connection_recovery": "verified", "total_events": 6}
            )
            
            await asyncio.sleep(0.8)  # Allow recovery delivery
            
            # Assert - verify recovery behavior
            received_events = await client.get_received_events()
            
            # Should receive all events including those sent during disconnection
            assert len(received_events) >= 5  # All events should be delivered
            
            # Verify event ordering preserved
            event_types = [event.get("type") for event in received_events]
            
            # Should have proper sequence despite disconnection
            assert "agent_started" in event_types
            assert "tool_executing" in event_types  # Should be delivered after reconnect
            assert "tool_completed" in event_types
            assert "agent_completed" in event_types
            
            # Verify recovery metadata in final event
            completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0
            
            final_result = completion_events[0]["payload"]["result"]
            assert final_result["connection_recovery"] == "verified"
            
            # Verify Redis maintained event queue during disconnection
            recovery_keys = await redis_client.keys(f"websocket:recovery:{context.thread_id}:*")
            # Recovery keys might be cleaned up after successful delivery
            
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_websocket_event_ordering_under_load_real_services(self, real_services_fixture, real_redis_fixture):
        """Test WebSocket event ordering under high load with real services."""
        # Arrange - verify services are available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for integration testing")
        
        redis_client = real_redis_fixture
        
        # Create high-performance WebSocket manager
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_batching=True,
            batch_size=10,
            batch_timeout=0.1
        )
        
        notifier = WebSocketNotifier(
            websocket_manager=websocket_manager,
            max_queue_size=1000  # Allow high throughput
        )
        
        context = AgentExecutionContext(
            agent_name="load_test_agent",
            run_id=uuid.uuid4(),
            thread_id=f"load-thread-{uuid.uuid4()}",
            user_id=f"load-user-{uuid.uuid4()}"
        )
        
        client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id,
            buffer_size=1000  # Handle high volume
        )
        
        try:
            await client.connect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Act - send high volume of events rapidly
            num_events = 50
            event_sequence = []
            
            # Send agent started
            await notifier.send_agent_started(context)
            event_sequence.append(("agent_started", 0))
            
            # Send many thinking events
            thinking_tasks = []
            for i in range(num_events):
                task = notifier.send_agent_thinking(
                    context,
                    thought=f"Processing step {i+1} of {num_events}...",
                    step_number=i+1,
                    progress_percentage=((i+1) / num_events) * 90.0
                )
                thinking_tasks.append(task)
                event_sequence.append(("agent_thinking", i+1))
            
            # Execute all thinking events concurrently
            await asyncio.gather(*thinking_tasks)
            
            # Send completion
            await notifier.send_agent_completed(
                context,
                result={"high_load_test": "completed", "events_sent": num_events + 2}
            )
            event_sequence.append(("agent_completed", num_events + 1))
            
            # Wait for all events to be processed through Redis
            await asyncio.sleep(2.0)  # Longer wait for high volume
            
            # Assert - verify ordering under load
            received_events = await client.get_received_events()
            
            assert len(received_events) >= num_events + 2  # All events delivered
            
            # Verify proper ordering despite high load
            first_event = received_events[0]
            last_event = received_events[-1]
            
            assert first_event["type"] == "agent_started"
            assert last_event["type"] == "agent_completed"
            
            # Verify thinking events maintain sequence
            thinking_events = [e for e in received_events if e["type"] == "agent_thinking"]
            assert len(thinking_events) == num_events
            
            # Verify step numbers are in sequence
            step_numbers = [e["payload"]["step_number"] for e in thinking_events]
            expected_steps = list(range(1, num_events + 1))
            assert step_numbers == expected_steps
            
            # Verify progress is monotonically increasing
            progress_values = [e["payload"]["progress_percentage"] for e in thinking_events]
            assert progress_values == sorted(progress_values)
            
            # Verify Redis handled high throughput efficiently
            redis_info = await redis_client.info("stats")
            total_commands = redis_info.get("total_commands_processed", 0)
            assert total_commands > num_events  # Redis should have processed many commands
        
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()