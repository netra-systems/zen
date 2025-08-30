"""
Mission Critical: Test Agent Manager WebSocket Lifecycle Events

CRITICAL: This test validates that agent lifecycle events are properly emitted
through WebSocket channels. These events are essential for frontend visibility.

Business Value: 
- Segment: Mid/Enterprise
- Goal: Real-time visibility into agent operations
- Impact: Critical for debugging and monitoring
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.supervisor.agent_manager import AgentManager, AgentStatus
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.websocket_core import WebSocketManager


class TestAgentManagerLifecycleEvents:
    """Test suite for agent manager WebSocket lifecycle events."""
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_to_thread = AsyncMock()
        manager.broadcast = AsyncMock()
        return manager
    
    @pytest.fixture
    async def websocket_notifier(self, websocket_manager):
        """Create WebSocket notifier."""
        return WebSocketNotifier(websocket_manager)
    
    @pytest.fixture
    async def agent_manager_with_websocket(self, websocket_notifier):
        """Create agent manager with WebSocket support."""
        manager = AgentManager(max_concurrent_agents=5)
        manager.websocket_notifier = websocket_notifier
        return manager
    
    @pytest.fixture
    async def mock_agent(self):
        """Create mock agent instance."""
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={"result": "success"})
        agent.process = AsyncMock(return_value={"result": "success"})
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_registration_emits_websocket_event(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that agent registration emits WebSocket event."""
        # Register agent with thread_id in metadata
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="test_agent",
            agent_instance=mock_agent,
            metadata={"capability": "testing", "thread_id": "test_thread_123"}
        )
        
        # Verify WebSocket event was sent
        websocket_manager.send_to_thread.assert_called()
        call_args = websocket_manager.send_to_thread.call_args
        
        # Check event structure
        assert call_args is not None
        event_data = call_args[0][1]  # Second argument is the message
        assert event_data["type"] == "agent_registered"
        assert "agent_id" in event_data["payload"]
        assert event_data["payload"]["agent_id"] == agent_id
        assert event_data["payload"]["agent_type"] == "test_agent"
        assert event_data["payload"]["status"] == "idle"
        assert "metadata" in event_data["payload"]
    
    @pytest.mark.asyncio
    async def test_agent_failure_emits_websocket_event(
        self, agent_manager_with_websocket, websocket_manager
    ):
        """Test that agent failure emits WebSocket event."""
        # Create failing agent
        failing_agent = AsyncMock()
        failing_agent.execute = AsyncMock(side_effect=Exception("Test failure"))
        
        # Register and start agent
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="failing_agent",
            agent_instance=failing_agent,
            metadata={"thread_id": "test_thread_fail"}
        )
        
        # Reset mock to clear registration event
        websocket_manager.send_to_thread.reset_mock()
        
        # Start task that will fail (doesn't raise since it's async)
        await agent_manager_with_websocket.start_agent_task(
            agent_id=agent_id,
            task_data={"task": "fail"}
        )
        # Wait for task to complete
        await asyncio.sleep(0.2)
        
        # Verify failure event was sent
        calls = websocket_manager.send_to_thread.call_args_list
        failure_event_sent = False
        
        for call in calls:
            event_data = call[0][1]
            if event_data["type"] == "agent_failed":
                failure_event_sent = True
                assert event_data["payload"]["agent_id"] == agent_id
                assert event_data["payload"]["status"] == "failed"
                assert "error" in event_data["payload"]
                assert "timestamp" in event_data["payload"]
                break
        
        assert failure_event_sent, "Agent failure event was not sent"
    
    @pytest.mark.asyncio
    async def test_agent_cancellation_emits_websocket_event(
        self, agent_manager_with_websocket, websocket_manager
    ):
        """Test that agent cancellation emits WebSocket event."""
        # Create slow agent
        slow_agent = AsyncMock()
        async def slow_execute(data):
            await asyncio.sleep(10)  # Long running task
            return {"result": "complete"}
        slow_agent.execute = slow_execute
        
        # Register agent
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="slow_agent",
            agent_instance=slow_agent,
            metadata={"thread_id": "test_thread_789"}
        )
        
        # Reset mock to clear registration event
        websocket_manager.send_to_thread.reset_mock()
        
        # Start task
        await agent_manager_with_websocket.start_agent_task(
            agent_id=agent_id,
            task_data={"task": "long_running"}
        )
        
        # Cancel task
        await agent_manager_with_websocket.stop_agent_task(agent_id)
        
        # Verify cancellation event was sent
        calls = websocket_manager.send_to_thread.call_args_list
        cancellation_event_sent = False
        
        for call in calls:
            event_data = call[0][1]
            if event_data["type"] == "agent_cancelled":
                cancellation_event_sent = True
                assert event_data["payload"]["agent_id"] == agent_id
                assert event_data["payload"]["status"] == "cancelled"
                assert "timestamp" in event_data["payload"]
                break
        
        assert cancellation_event_sent, "Agent cancellation event was not sent"
    
    @pytest.mark.asyncio
    async def test_agent_metrics_update_emits_websocket_event(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that agent metrics updates emit WebSocket events."""
        # Register agent
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="metrics_agent",
            agent_instance=mock_agent,
            metadata={"thread_id": "test_thread_metrics"}
        )
        
        # Start and complete task
        await agent_manager_with_websocket.start_agent_task(
            agent_id=agent_id,
            task_data={"task": "metrics_test"}
        )
        
        # Wait for task completion
        await asyncio.sleep(0.1)
        
        # Get metrics
        metrics = await agent_manager_with_websocket.get_agent_metrics(agent_id)
        
        # Reset mock to check for metrics event
        websocket_manager.send_to_thread.reset_mock()
        
        # Trigger metrics update (should emit event)
        system_metrics = await agent_manager_with_websocket.get_system_metrics()
        
        # Verify metrics event was sent
        calls = websocket_manager.send_to_thread.call_args_list
        metrics_event_sent = False
        
        for call in calls:
            event_data = call[0][1]
            if event_data["type"] == "agent_metrics_updated":
                metrics_event_sent = True
                assert "system_metrics" in event_data["payload"]
                assert "total_agents" in event_data["payload"]["system_metrics"]
                assert "running_agents" in event_data["payload"]["system_metrics"]
                assert "total_tasks_completed" in event_data["payload"]["system_metrics"]
                assert "timestamp" in event_data["payload"]
                break
        
        assert metrics_event_sent, "Agent metrics update event was not sent"
    
    @pytest.mark.asyncio
    async def test_agent_unregistration_emits_websocket_event(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that agent unregistration emits WebSocket event."""
        # Register agent
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="temp_agent",
            agent_instance=mock_agent,
            metadata={"thread_id": "test_thread_456"}
        )
        
        # Reset mock to clear registration event
        websocket_manager.send_to_thread.reset_mock()
        
        # Unregister agent
        success = await agent_manager_with_websocket.unregister_agent(agent_id)
        assert success
        
        # Verify unregistration event was sent
        websocket_manager.send_to_thread.assert_called()
        call_args = websocket_manager.send_to_thread.call_args
        event_data = call_args[0][1]
        
        assert event_data["type"] == "agent_unregistered"
        assert event_data["payload"]["agent_id"] == agent_id
        assert "timestamp" in event_data["payload"]
    
    @pytest.mark.asyncio
    async def test_agent_status_transition_events(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that all status transitions emit appropriate events."""
        # Register agent
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="status_agent",
            agent_instance=mock_agent,
            metadata={"thread_id": "test_thread_status"}
        )
        
        # Reset mock to track status events
        websocket_manager.send_to_thread.reset_mock()
        
        # Start task (IDLE -> RUNNING)
        await agent_manager_with_websocket.start_agent_task(
            agent_id=agent_id,
            task_data={"task": "status_test"}
        )
        
        # Wait for completion (RUNNING -> COMPLETED)
        await asyncio.sleep(0.1)
        await agent_manager_with_websocket.cleanup_completed_tasks()
        
        # Verify status transition events
        calls = websocket_manager.send_to_thread.call_args_list
        event_types = [call[0][1]["type"] for call in calls]
        
        assert "agent_status_changed" in event_types
        
        # Check for specific transitions
        status_events = [
            call[0][1] for call in calls 
            if call[0][1]["type"] == "agent_status_changed"
        ]
        
        # Should have IDLE->RUNNING and RUNNING->COMPLETED transitions
        assert len(status_events) >= 2
        
        # Verify transition details
        for event in status_events:
            assert "agent_id" in event["payload"]
            assert "old_status" in event["payload"]
            assert "new_status" in event["payload"]
            assert "timestamp" in event["payload"]
    
    @pytest.mark.asyncio
    async def test_bulk_agent_operations_emit_events(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that bulk operations emit appropriate events."""
        agent_ids = []
        
        # Register multiple agents
        for i in range(3):
            agent_id = await agent_manager_with_websocket.register_agent(
                agent_type=f"bulk_agent_{i}",
                agent_instance=mock_agent,
                metadata={"index": i, "thread_id": f"test_thread_bulk_{i}"}
            )
            agent_ids.append(agent_id)
        
        # Reset mock
        websocket_manager.send_to_thread.reset_mock()
        
        # Shutdown (should emit events for all agents)
        await agent_manager_with_websocket.shutdown()
        
        # Verify shutdown events
        calls = websocket_manager.send_to_thread.call_args_list
        shutdown_events = [
            call[0][1] for call in calls 
            if call[0][1]["type"] == "agent_manager_shutdown"
        ]
        
        assert len(shutdown_events) > 0
        shutdown_event = shutdown_events[0]
        assert "agents_affected" in shutdown_event["payload"]
        assert shutdown_event["payload"]["agents_affected"] == len(agent_ids)
    
    @pytest.mark.asyncio
    async def test_event_includes_execution_context(
        self, agent_manager_with_websocket, mock_agent, websocket_manager
    ):
        """Test that events include proper execution context."""
        # Register agent with specific metadata
        agent_id = await agent_manager_with_websocket.register_agent(
            agent_type="context_agent",
            agent_instance=mock_agent,
            metadata={
                "thread_id": "test_thread_123",
                "user_id": "user_456",
                "session_id": "session_789"
            }
        )
        
        # Verify registration event includes context
        call_args = websocket_manager.send_to_thread.call_args
        event_data = call_args[0][1]
        
        assert "metadata" in event_data["payload"]
        metadata = event_data["payload"]["metadata"]
        assert metadata["thread_id"] == "test_thread_123"
        assert metadata["user_id"] == "user_456"
        assert metadata["session_id"] == "session_789"
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_events_are_ordered(
        self, agent_manager_with_websocket, websocket_manager
    ):
        """Test that concurrent agent events maintain proper ordering."""
        agents = []
        agent_ids = []
        
        # Create multiple agents with different execution times
        for i in range(3):
            agent = AsyncMock()
            async def execute_with_delay(data, delay=i*0.1):
                await asyncio.sleep(delay)
                return {"result": f"completed_{i}"}
            agent.execute = execute_with_delay
            agents.append(agent)
            
            agent_id = await agent_manager_with_websocket.register_agent(
                agent_type=f"concurrent_agent_{i}",
                agent_instance=agent,
                metadata={"thread_id": f"test_thread_concurrent_{i}"}
            )
            agent_ids.append(agent_id)
        
        # Reset mock
        websocket_manager.send_to_thread.reset_mock()
        
        # Start all agents concurrently
        tasks = []
        for agent_id in agent_ids:
            task = agent_manager_with_websocket.start_agent_task(
                agent_id=agent_id,
                task_data={"task": "concurrent"}
            )
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)
        
        # Verify events were sent in proper order
        calls = websocket_manager.send_to_thread.call_args_list
        
        # Each agent should have start and complete events
        for agent_id in agent_ids:
            agent_events = [
                call[0][1] for call in calls
                if call[0][1].get("payload", {}).get("agent_id") == agent_id
            ]
            
            # Should have at least status change events
            assert len(agent_events) >= 1
            
            # Verify timestamps are in order
            timestamps = [
                event["payload"].get("timestamp", 0) 
                for event in agent_events
            ]
            assert timestamps == sorted(timestamps)


class TestWebSocketNotifierIntegration:
    """Test WebSocket notifier integration with agent manager."""
    
    @pytest.mark.asyncio
    async def test_notifier_methods_available(self):
        """Test that all required notifier methods exist."""
        websocket_manager = AsyncMock(spec=WebSocketManager)
        notifier = WebSocketNotifier(websocket_manager)
        
        # Verify lifecycle event methods exist (these need to be added)
        required_methods = [
            "send_agent_registered",
            "send_agent_failed", 
            "send_agent_cancelled",
            "send_agent_metrics_updated",
            "send_agent_unregistered",
            "send_agent_status_changed",
            "send_agent_manager_shutdown"
        ]
        
        for method_name in required_methods:
            # These methods don't exist yet - they need to be implemented
            assert hasattr(notifier, method_name), f"Missing method: {method_name}"
    
    @pytest.mark.asyncio
    async def test_event_payload_structure(self):
        """Test that event payloads have correct structure."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        websocket_manager = AsyncMock(spec=WebSocketManager)
        notifier = WebSocketNotifier(websocket_manager)
        
        # Create a mock context for testing
        context = AgentExecutionContext(
            agent_name="test_agent",
            thread_id="test_thread",
            run_id="test_run",
            user_id="test_user"
        )
        
        # Test structures for new lifecycle events
        test_cases = [
            {
                "method": "send_agent_registered",
                "args": {
                    "context": context,
                    "agent_id": "test_123",
                    "agent_type": "test",
                    "agent_metadata": {"key": "value"}
                },
                "expected_type": "agent_registered",
                "required_fields": ["agent_id", "agent_type", "status", "timestamp"]
            },
            {
                "method": "send_agent_failed",
                "args": {
                    "context": context,
                    "agent_id": "test_123",
                    "error": "Test error message"
                },
                "expected_type": "agent_failed",
                "required_fields": ["agent_id", "status", "error", "timestamp"]
            },
            {
                "method": "send_agent_cancelled",
                "args": {
                    "context": context,
                    "agent_id": "test_123"
                },
                "expected_type": "agent_cancelled",
                "required_fields": ["agent_id", "status", "timestamp"]
            }
        ]
        
        for test_case in test_cases:
            method = getattr(notifier, test_case["method"], None)
            if method:
                await method(**test_case["args"])
                
                # Verify WebSocket send was called
                assert websocket_manager.send_to_thread.called
                
                # Check payload structure
                call_args = websocket_manager.send_to_thread.call_args
                message = call_args[0][1]
                
                assert message["type"] == test_case["expected_type"]
                for field in test_case["required_fields"]:
                    assert field in message["payload"]
                
                # Reset for next test
                websocket_manager.send_to_thread.reset_mock()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])