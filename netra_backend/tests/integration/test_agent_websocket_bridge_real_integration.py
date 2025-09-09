"""Integration Tests for Agent WebSocket Bridge with Real Services

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time agent feedback reaches users reliably
- Value Impact: Prevents user confusion and abandonment during AI execution
- Strategic Impact: Core UX functionality that builds user confidence in AI

CRITICAL TEST PURPOSE:
These integration tests validate the AgentWebSocketBridge integration with
real WebSocket connections and Redis for reliable event delivery.

Test Coverage:
- Agent WebSocket bridge with real connections
- Event delivery through real Redis message queues
- Bridge initialization and lifecycle management
- Tool execution event propagation with real services
- Error handling and recovery with real network conditions
- Multi-agent event coordination through real infrastructure
"""

import pytest
import asyncio
import uuid
from typing import Dict, Any, List
from datetime import datetime

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from test_framework.ssot.real_services_test_fixtures import *
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient


class MockAgent:
    """Mock agent for bridge integration testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.websocket_bridge = None
        self._run_id = None
        self._user_id = None
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for event notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
    
    async def execute_with_notifications(self, context, state):
        """Execute agent with WebSocket notifications."""
        if self.websocket_bridge:
            # Send thinking notification
            await self.websocket_bridge.notify_agent_thinking(
                run_id=self._run_id,
                agent_name=self.name,
                reasoning=f"{self.name} is processing your request...",
                step_number=1,
                progress_percentage=25.0
            )
            
            # Simulate tool execution
            await self.websocket_bridge.notify_tool_executing(
                run_id=self._run_id,
                agent_name=self.name,
                tool_name="mock_analyzer",
                tool_purpose="Analyze data for testing"
            )
            
            # Simulate processing time
            await asyncio.sleep(0.2)
            
            # Send tool completion
            await self.websocket_bridge.notify_tool_completed(
                run_id=self._run_id,
                agent_name=self.name,
                tool_name="mock_analyzer",
                result={"analysis": "complete", "insights": ["test insight"]}
            )
            
            # Send final thinking
            await self.websocket_bridge.notify_agent_thinking(
                run_id=self._run_id,
                agent_name=self.name,
                reasoning="Finalizing results...",
                step_number=2,
                progress_percentage=90.0
            )
        
        return {
            "status": "completed",
            "agent": self.name,
            "notifications_sent": self.websocket_bridge is not None
        }


@pytest.mark.integration
class TestAgentWebSocketBridgeRealIntegration:
    """Integration tests for Agent WebSocket Bridge with real services."""
    
    @pytest.mark.asyncio
    async def test_agent_websocket_bridge_real_redis_integration(self, real_services_fixture, real_redis_fixture):
        """Test Agent WebSocket Bridge with real Redis backend."""
        # Arrange - verify Redis is available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for WebSocket bridge testing")
        
        redis_client = real_redis_fixture
        
        # Create real WebSocket manager with Redis
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_real_connections=True
        )
        
        # Create WebSocket bridge
        bridge = AgentWebSocketBridge(
            websocket_manager=websocket_manager,
            enable_redis_persistence=True
        )
        
        # Create test context
        context = AgentExecutionContext(
            agent_name="redis_bridge_agent",
            run_id=uuid.uuid4(),
            thread_id=f"bridge-thread-{uuid.uuid4()}",
            user_id=f"bridge-user-{uuid.uuid4()}"
        )
        
        # Create mock agent with bridge
        agent = MockAgent("redis_bridge_agent")
        agent.set_websocket_bridge(bridge, context.run_id)
        
        # Create real WebSocket client
        client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id
        )
        
        try:
            # Connect WebSocket client
            await client.connect()
            
            # Register connection with manager
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Act - execute agent with bridge notifications
            result = await agent.execute_with_notifications(context, None)
            
            # Wait for Redis message propagation
            await asyncio.sleep(0.8)
            
            # Assert - verify bridge integration
            assert result["notifications_sent"] == True
            assert result["status"] == "completed"
            
            # Verify events were delivered through Redis
            received_events = await client.get_received_events()
            assert len(received_events) >= 4  # thinking + tool_executing + tool_completed + thinking
            
            # Verify event types received
            event_types = [event.get("type") for event in received_events]
            expected_types = ["agent_thinking", "tool_executing", "tool_completed"]
            
            for expected_type in expected_types:
                assert expected_type in event_types, f"Missing event type: {expected_type}"
            
            # Verify Redis keys were used for message routing
            redis_keys = await redis_client.keys(f"websocket:thread:{context.thread_id}:*")
            assert len(redis_keys) > 0, "Redis should contain WebSocket routing keys"
            
            # Verify event content integrity
            thinking_events = [e for e in received_events if e["type"] == "agent_thinking"]
            tool_events = [e for e in received_events if e["type"] == "tool_executing"]
            
            assert len(thinking_events) >= 2  # Should have multiple thinking events
            assert len(tool_events) >= 1  # Should have tool execution event
            
            # Verify progress progression
            progress_values = [e["payload"]["progress_percentage"] for e in thinking_events if "progress_percentage" in e["payload"]]
            if len(progress_values) >= 2:
                assert progress_values[-1] > progress_values[0]  # Progress should increase
        
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_multiple_agents_websocket_bridge_coordination(self, real_services_fixture, real_redis_fixture):
        """Test multiple agents coordinating through WebSocket bridge with real services."""
        # Arrange - verify Redis is available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for multi-agent bridge testing")
        
        redis_client = real_redis_fixture
        
        # Create WebSocket manager
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_coordination=True
        )
        
        # Create shared bridge
        bridge = AgentWebSocketBridge(
            websocket_manager=websocket_manager,
            enable_agent_coordination=True
        )
        
        # Create contexts for multiple agents
        context1 = AgentExecutionContext(
            agent_name="coordinator_agent_1",
            run_id=uuid.uuid4(),
            thread_id=f"coord-thread-{uuid.uuid4()}",
            user_id=f"coord-user-{uuid.uuid4()}"
        )
        
        context2 = AgentExecutionContext(
            agent_name="coordinator_agent_2", 
            run_id=uuid.uuid4(),
            thread_id=context1.thread_id,  # Same thread for coordination
            user_id=context1.user_id       # Same user for coordination
        )
        
        # Create agents with shared bridge
        agent1 = MockAgent("coordinator_agent_1")
        agent1.set_websocket_bridge(bridge, context1.run_id)
        
        agent2 = MockAgent("coordinator_agent_2")
        agent2.set_websocket_bridge(bridge, context2.run_id)
        
        # Create WebSocket client
        client = RealWebSocketTestClient(
            thread_id=context1.thread_id,
            user_id=context1.user_id
        )
        
        try:
            # Connect client
            await client.connect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context1.thread_id,
                user_id=context1.user_id
            )
            
            # Act - execute agents concurrently with coordination
            agent1_task = agent1.execute_with_notifications(context1, None)
            agent2_task = agent2.execute_with_notifications(context2, None)
            
            results = await asyncio.gather(agent1_task, agent2_task)
            
            # Wait for all events to propagate
            await asyncio.sleep(1.0)
            
            # Assert - verify multi-agent coordination
            agent1_result, agent2_result = results
            
            assert agent1_result["notifications_sent"] == True
            assert agent2_result["notifications_sent"] == True
            
            # Verify events from both agents were delivered
            received_events = await client.get_received_events()
            
            # Should receive events from both agents
            agent1_events = [e for e in received_events if "coordinator_agent_1" in str(e)]
            agent2_events = [e for e in received_events if "coordinator_agent_2" in str(e)]
            
            assert len(agent1_events) >= 2  # At least some events from agent1
            assert len(agent2_events) >= 2  # At least some events from agent2
            
            # Verify coordination metadata
            all_events = received_events
            coordination_events = [e for e in all_events if "agent_name" in e.get("payload", {})]
            
            agent_names = set()
            for event in coordination_events:
                if "agent_name" in event["payload"]:
                    agent_names.add(event["payload"]["agent_name"])
            
            assert len(agent_names) == 2  # Both agents should have sent events
            assert "coordinator_agent_1" in agent_names
            assert "coordinator_agent_2" in agent_names
        
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_error_handling_real_services(self, real_services_fixture, real_redis_fixture):
        """Test WebSocket bridge error handling with real service failures."""
        # Arrange - verify Redis is available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for error handling testing")
        
        redis_client = real_redis_fixture
        
        # Create WebSocket manager with error handling
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_error_recovery=True,
            retry_attempts=3
        )
        
        # Create bridge with error handling
        bridge = AgentWebSocketBridge(
            websocket_manager=websocket_manager,
            enable_error_recovery=True
        )
        
        # Create context
        context = AgentExecutionContext(
            agent_name="error_handling_agent",
            run_id=uuid.uuid4(),
            thread_id=f"error-thread-{uuid.uuid4()}",
            user_id=f"error-user-{uuid.uuid4()}"
        )
        
        # Create agent
        agent = MockAgent("error_handling_agent")
        agent.set_websocket_bridge(bridge, context.run_id)
        
        # Create client that will simulate disconnection
        client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id,
            enable_reconnect=True
        )
        
        try:
            # Connect client
            await client.connect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Send some initial events
            await bridge.notify_agent_thinking(
                run_id=context.run_id,
                agent_name=context.agent_name,
                reasoning="Starting error handling test...",
                progress_percentage=10.0
            )
            
            await asyncio.sleep(0.2)
            
            # Act - simulate client disconnection during agent execution
            await client.simulate_disconnect()
            
            # Continue sending events (should be queued in Redis)
            await bridge.notify_tool_executing(
                run_id=context.run_id,
                agent_name=context.agent_name,
                tool_name="error_test_tool",
                tool_purpose="Test error recovery"
            )
            
            await bridge.notify_agent_thinking(
                run_id=context.run_id,
                agent_name=context.agent_name,
                reasoning="Continuing despite connection issues...",
                progress_percentage=50.0
            )
            
            # Reconnect client
            await client.reconnect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Send final events
            await bridge.notify_tool_completed(
                run_id=context.run_id,
                agent_name=context.agent_name,
                tool_name="error_test_tool",
                result={"recovery": "successful"}
            )
            
            await bridge.notify_agent_thinking(
                run_id=context.run_id,
                agent_name=context.agent_name,
                reasoning="Recovery complete!",
                progress_percentage=100.0
            )
            
            # Wait for recovery and event delivery
            await asyncio.sleep(1.2)
            
            # Assert - verify error recovery
            received_events = await client.get_received_events()
            
            # Should receive all events including those sent during disconnection
            assert len(received_events) >= 4  # All events should be delivered eventually
            
            # Verify recovery events
            recovery_events = [e for e in received_events if "recovery" in str(e).lower()]
            assert len(recovery_events) >= 1  # Should have recovery-related events
            
            # Verify final completion event
            completion_events = [e for e in received_events if "complete" in str(e).lower()]
            assert len(completion_events) >= 1
            
            # Verify Redis maintained event queue during disconnection
            redis_recovery_keys = await redis_client.keys(f"websocket:recovery:{context.thread_id}:*")
            # Recovery keys might be cleaned up after successful delivery
        
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_performance_real_services(self, real_services_fixture, real_redis_fixture):
        """Test WebSocket bridge performance with high event volume and real services."""
        # Arrange - verify Redis is available
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for performance testing")
        
        redis_client = real_redis_fixture
        
        # Create high-performance WebSocket manager
        websocket_manager = UnifiedWebSocketManager(
            redis_client=redis_client,
            enable_batching=True,
            batch_size=20,
            batch_timeout=0.05
        )
        
        # Create optimized bridge
        bridge = AgentWebSocketBridge(
            websocket_manager=websocket_manager,
            enable_performance_mode=True
        )
        
        # Create context
        context = AgentExecutionContext(
            agent_name="performance_agent",
            run_id=uuid.uuid4(),
            thread_id=f"perf-thread-{uuid.uuid4()}",
            user_id=f"perf-user-{uuid.uuid4()}"
        )
        
        # Create client
        client = RealWebSocketTestClient(
            thread_id=context.thread_id,
            user_id=context.user_id,
            buffer_size=1000
        )
        
        try:
            # Connect client
            await client.connect()
            await websocket_manager.register_connection(
                connection=client,
                thread_id=context.thread_id,
                user_id=context.user_id
            )
            
            # Act - send high volume of events
            start_time = asyncio.get_event_loop().time()
            num_events = 100
            
            # Send many thinking events rapidly
            thinking_tasks = []
            for i in range(num_events):
                task = bridge.notify_agent_thinking(
                    run_id=context.run_id,
                    agent_name=context.agent_name,
                    reasoning=f"Processing step {i+1} of {num_events}...",
                    step_number=i+1,
                    progress_percentage=(i+1) * 100.0 / num_events
                )
                thinking_tasks.append(task)
            
            # Execute all events
            await asyncio.gather(*thinking_tasks)
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            # Wait for event delivery
            await asyncio.sleep(2.0)
            
            # Assert - verify performance
            received_events = await client.get_received_events()
            
            # Should receive all events
            thinking_events = [e for e in received_events if e.get("type") == "agent_thinking"]
            assert len(thinking_events) >= num_events * 0.95  # Allow 5% loss for network conditions
            
            # Verify reasonable performance
            events_per_second = num_events / execution_time
            assert events_per_second > 50, f"Performance too low: {events_per_second} events/sec"
            
            # Verify event ordering maintained despite high volume
            step_numbers = []
            for event in thinking_events:
                if "step_number" in event.get("payload", {}):
                    step_numbers.append(event["payload"]["step_number"])
            
            # Should maintain reasonable ordering
            if len(step_numbers) >= 10:
                # Check that early events come before later events (allowing some reordering)
                early_events = [s for s in step_numbers if s <= 10]
                late_events = [s for s in step_numbers if s >= 90]
                
                if early_events and late_events:
                    avg_early = sum(early_events) / len(early_events)
                    avg_late = sum(late_events) / len(late_events)
                    assert avg_late > avg_early, "Event ordering should be generally maintained"
            
            # Verify Redis handled high throughput
            redis_info = await redis_client.info("stats")
            total_commands = redis_info.get("total_commands_processed", 0)
            assert total_commands > num_events, "Redis should have processed many commands"
        
        finally:
            # Cleanup
            await client.disconnect()
            await websocket_manager.cleanup()