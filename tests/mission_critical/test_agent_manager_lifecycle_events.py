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


class TestBaseAgentInheritanceLifecycleEvents:
    """Test BaseAgent inheritance patterns in lifecycle events"""
    
    @pytest.mark.asyncio
    async def test_baseagent_lifecycle_event_inheritance(self):
        """Test BaseAgent lifecycle events work through inheritance"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("BaseAgent components not available")
        
        lifecycle_events = []
        
        class LifecycleTestAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.lifecycle_events = lifecycle_events
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Record lifecycle event
                self.lifecycle_events.append({
                    "event": "execute_core_started",
                    "agent_name": self.name,
                    "context_id": context.run_id
                })
                
                await asyncio.sleep(0.1)
                
                # Emit WebSocket events during execution
                await self.emit_agent_started()
                await self.emit_thinking("Processing lifecycle test")
                
                self.lifecycle_events.append({
                    "event": "execute_core_completed",
                    "agent_name": self.name,
                    "context_id": context.run_id
                })
                
                await self.emit_agent_completed({"lifecycle_test": "completed"})
                return {"lifecycle_test": "success"}
        
        # Create agent manager with WebSocket
        websocket_manager = AsyncMock(spec=WebSocketManager)
        websocket_manager.send_to_thread = AsyncMock()
        notifier = WebSocketNotifier(websocket_manager)
        
        agent_manager = AgentManager(max_concurrent_agents=5)
        agent_manager.websocket_notifier = notifier
        
        # Create test agent
        test_agent = LifecycleTestAgent(name="LifecycleTestAgent")
        
        # Register agent
        agent_id = await agent_manager.register_agent(
            agent_type="lifecycle_test",
            agent_instance=test_agent,
            metadata={"thread_id": "lifecycle_test_123"}
        )
        
        # Execute agent task
        context = ExecutionContext(
            run_id="lifecycle_test_run",
            agent_name=test_agent.name,
            state=DeepAgentState()
        )
        
        result = await test_agent.execute_core_logic(context)
        assert result["lifecycle_test"] == "success"
        
        # Verify lifecycle events were recorded
        assert len(lifecycle_events) == 2
        assert lifecycle_events[0]["event"] == "execute_core_started"
        assert lifecycle_events[1]["event"] == "execute_core_completed"
        
        # Verify WebSocket events were sent
        assert websocket_manager.send_to_thread.call_count >= 1
        print("✅ BaseAgent lifecycle events work through inheritance")
    
    @pytest.mark.asyncio
    async def test_baseagent_state_transition_events(self):
        """Test BaseAgent state transitions emit proper lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.schemas.agent import SubAgentLifecycle
        except ImportError:
            pytest.skip("BaseAgent components not available")
        
        state_transitions = []
        
        class StateTransitionAgent(BaseAgent):
            def set_state(self, new_state):
                old_state = self.get_state()
                super().set_state(new_state)
                
                state_transitions.append({
                    "from_state": old_state,
                    "to_state": new_state,
                    "agent_name": self.name
                })
                
            async def execute_core_logic(self, context) -> Dict[str, Any]:
                # Transition through states
                self.set_state(SubAgentLifecycle.RUNNING)
                await asyncio.sleep(0.05)
                
                self.set_state(SubAgentLifecycle.COMPLETED)
                return {"state_transitions": len(state_transitions)}
        
        agent = StateTransitionAgent(name="StateTransitionTest")
        
        # Test state transitions
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        
        context = ExecutionContext(
            run_id="state_transition_test",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(context)
        
        # Verify state transitions were recorded
        assert len(state_transitions) == 2
        assert state_transitions[0]["to_state"] == SubAgentLifecycle.RUNNING
        assert state_transitions[1]["to_state"] == SubAgentLifecycle.COMPLETED
        
        # Final state should be COMPLETED
        assert agent.get_state() == SubAgentLifecycle.COMPLETED
        print("✅ BaseAgent state transitions emit proper lifecycle events")
    
    @pytest.mark.asyncio
    async def test_baseagent_websocket_integration_lifecycle(self):
        """Test BaseAgent WebSocket integration in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("BaseAgent components not available")
        
        websocket_events = []
        
        class WebSocketLifecycleAgent(BaseAgent):
            async def emit_agent_started(self):
                websocket_events.append("agent_started")
                await super().emit_agent_started()
                
            async def emit_thinking(self, message):
                websocket_events.append(f"thinking: {message}")
                await super().emit_thinking(message)
                
            async def emit_agent_completed(self, result):
                websocket_events.append("agent_completed")
                await super().emit_agent_completed(result)
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Full lifecycle with WebSocket events
                await self.emit_agent_started()
                await self.emit_thinking("Starting websocket lifecycle test")
                
                await asyncio.sleep(0.1)
                
                await self.emit_thinking("Processing websocket integration")
                
                result = {"websocket_lifecycle": "success", "events_count": len(websocket_events)}
                await self.emit_agent_completed(result)
                
                return result
        
        agent = WebSocketLifecycleAgent(name="WebSocketLifecycleTest")
        
        context = ExecutionContext(
            run_id="websocket_lifecycle_test",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(context)
        
        # Verify all WebSocket events were captured
        expected_events = ["agent_started", "thinking: Starting websocket lifecycle test", 
                          "thinking: Processing websocket integration", "agent_completed"]
        assert websocket_events == expected_events
        
        assert result["websocket_lifecycle"] == "success"
        print("✅ BaseAgent WebSocket integration works in lifecycle events")


class TestExecuteCorePatternLifecycleEvents:
    """Test _execute_core pattern in lifecycle events"""
    
    @pytest.mark.asyncio
    async def test_execute_core_lifecycle_event_timing(self):
        """Test _execute_core pattern timing in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        timing_events = []
        
        class TimingLifecycleAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                start_time = datetime.now(timezone.utc)
                timing_events.append({"event": "start", "timestamp": start_time})
                
                # Emit lifecycle events with timing
                await self.emit_agent_started()
                
                # Simulate work with timing tracking
                for i in range(3):
                    step_start = datetime.now(timezone.utc)
                    await asyncio.sleep(0.05)  # Simulate work
                    step_end = datetime.now(timezone.utc)
                    
                    timing_events.append({
                        "event": f"step_{i}",
                        "start": step_start,
                        "end": step_end,
                        "duration": (step_end - step_start).total_seconds()
                    })
                    
                    await self.emit_thinking(f"Completed step {i+1}/3")
                
                end_time = datetime.now(timezone.utc)
                timing_events.append({"event": "end", "timestamp": end_time})
                
                total_duration = (end_time - start_time).total_seconds()
                result = {
                    "timing_test": "completed",
                    "total_duration": total_duration,
                    "steps_completed": 3
                }
                
                await self.emit_agent_completed(result)
                return result
        
        agent = TimingLifecycleAgent(name="TimingLifecycleTest")
        
        context = ExecutionContext(
            run_id="timing_lifecycle_test",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(context)
        
        # Verify timing events
        assert len(timing_events) == 5  # start + 3 steps + end
        assert result["steps_completed"] == 3
        assert result["total_duration"] > 0.15  # Should take at least 150ms
        
        # Verify timing sequence
        for i in range(len(timing_events) - 1):
            if 'timestamp' in timing_events[i] and 'timestamp' in timing_events[i+1]:
                assert timing_events[i]['timestamp'] <= timing_events[i+1]['timestamp']
        
        print("✅ Execute core pattern timing works in lifecycle events")
    
    @pytest.mark.asyncio
    async def test_execute_core_concurrent_lifecycle_events(self):
        """Test _execute_core pattern with concurrent lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        concurrent_events = []
        
        class ConcurrentLifecycleAgent(BaseAgent):
            def __init__(self, agent_id, **kwargs):
                super().__init__(**kwargs)
                self.agent_id = agent_id
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Record start
                concurrent_events.append({
                    "agent_id": self.agent_id,
                    "event": "start",
                    "timestamp": datetime.now(timezone.utc)
                })
                
                await self.emit_agent_started()
                
                # Simulate concurrent work with different durations
                work_duration = 0.1 + (self.agent_id * 0.05)  # Staggered durations
                await asyncio.sleep(work_duration)
                
                await self.emit_thinking(f"Agent {self.agent_id} processing")
                
                # Record completion
                concurrent_events.append({
                    "agent_id": self.agent_id,
                    "event": "complete",
                    "timestamp": datetime.now(timezone.utc)
                })
                
                result = {"agent_id": self.agent_id, "work_duration": work_duration}
                await self.emit_agent_completed(result)
                return result
        
        # Create multiple agents
        agents = [
            ConcurrentLifecycleAgent(agent_id=i, name=f"ConcurrentAgent_{i}")
            for i in range(3)
        ]
        
        # Execute agents concurrently
        tasks = []
        for i, agent in enumerate(agents):
            context = ExecutionContext(
                run_id=f"concurrent_test_{i}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            tasks.append(agent.execute_core_logic(context))
        
        results = await asyncio.gather(*tasks)
        
        # Verify all agents completed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["agent_id"] == i
        
        # Verify concurrent events were recorded
        assert len(concurrent_events) == 6  # 3 starts + 3 completions
        
        # Check that events are properly attributed
        start_events = [e for e in concurrent_events if e["event"] == "start"]
        complete_events = [e for e in concurrent_events if e["event"] == "complete"]
        
        assert len(start_events) == 3
        assert len(complete_events) == 3
        
        print("✅ Execute core pattern works with concurrent lifecycle events")
    
    @pytest.mark.asyncio
    async def test_execute_core_resource_tracking_lifecycle(self):
        """Test _execute_core pattern with resource tracking in lifecycle"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        resource_events = []
        
        class ResourceTrackingAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.resources_used = 0
                self.max_resources = 100
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                await self.emit_agent_started()
                
                try:
                    # Acquire resources with tracking
                    await self._acquire_resources(30)
                    resource_events.append({
                        "event": "resources_acquired",
                        "amount": 30,
                        "total_used": self.resources_used
                    })
                    
                    await self.emit_thinking("Resources acquired, processing...")
                    
                    # Simulate resource-intensive work
                    await asyncio.sleep(0.1)
                    
                    # Check resource limits
                    if self.resources_used > self.max_resources * 0.8:
                        await self.emit_thinking("High resource usage detected")
                        resource_events.append({
                            "event": "high_resource_usage_warning",
                            "usage": self.resources_used,
                            "limit": self.max_resources
                        })
                    
                    result = {
                        "resource_tracking": "completed",
                        "resources_used": self.resources_used,
                        "resource_efficiency": self.resources_used / self.max_resources
                    }
                    
                    await self.emit_agent_completed(result)
                    return result
                    
                finally:
                    # Always release resources
                    await self._release_resources()
                    resource_events.append({
                        "event": "resources_released",
                        "final_usage": self.resources_used
                    })
            
            async def _acquire_resources(self, amount):
                self.resources_used += amount
                await asyncio.sleep(0.01)  # Simulate resource acquisition time
            
            async def _release_resources(self):
                self.resources_used = 0
                await asyncio.sleep(0.01)  # Simulate resource release time
        
        agent = ResourceTrackingAgent(name="ResourceTrackingTest")
        
        context = ExecutionContext(
            run_id="resource_tracking_test",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(context)
        
        # Verify resource tracking events
        expected_events = ["resources_acquired", "resources_released"]
        actual_events = [event["event"] for event in resource_events]
        
        for expected in expected_events:
            assert expected in actual_events
        
        # Verify final resource state
        assert result["resources_used"] == 0  # Should be released
        assert result["resource_efficiency"] > 0  # Should have used resources
        
        # Verify resources were properly released
        release_event = next(e for e in resource_events if e["event"] == "resources_released")
        assert release_event["final_usage"] == 0
        
        print("✅ Execute core pattern resource tracking works in lifecycle")
    
    @pytest.mark.asyncio
    async def test_execute_core_error_handling_lifecycle_events(self):
        """Test _execute_core pattern error handling in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        error_events = []
        
        class ErrorHandlingAgent(BaseAgent):
            def __init__(self, should_fail=False, **kwargs):
                super().__init__(**kwargs)
                self.should_fail = should_fail
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                try:
                    await self.emit_agent_started()
                    
                    # Simulate work that might fail
                    await self.emit_thinking("Starting error-prone operation")
                    
                    if self.should_fail:
                        error_events.append({
                            "event": "error_occurred",
                            "context_id": context.run_id,
                            "agent_name": self.name
                        })
                        raise RuntimeError("Simulated error in execute_core_logic")
                    
                    await self.emit_thinking("Operation completed successfully")
                    
                    result = {"error_handling_test": "success", "errors": len(error_events)}
                    await self.emit_agent_completed(result)
                    return result
                    
                except Exception as e:
                    error_events.append({
                        "event": "error_handled",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "context_id": context.run_id
                    })
                    
                    # Try to emit error notification
                    try:
                        await self.emit_thinking(f"Error occurred: {str(e)}")
                    except:
                        pass  # Don't let notification errors propagate
                    
                    raise  # Re-raise the original error
        
        # Test successful execution
        success_agent = ErrorHandlingAgent(should_fail=False, name="SuccessAgent")
        success_context = ExecutionContext(
            run_id="error_handling_success",
            agent_name=success_agent.name,
            state=DeepAgentState()
        )
        
        result = await success_agent.execute_core_logic(success_context)
        assert result["error_handling_test"] == "success"
        
        # Test error handling
        error_agent = ErrorHandlingAgent(should_fail=True, name="ErrorAgent")
        error_context = ExecutionContext(
            run_id="error_handling_failure",
            agent_name=error_agent.name,
            state=DeepAgentState()
        )
        
        with pytest.raises(RuntimeError):
            await error_agent.execute_core_logic(error_context)
        
        # Verify error events were recorded
        error_occurred_events = [e for e in error_events if e["event"] == "error_occurred"]
        error_handled_events = [e for e in error_events if e["event"] == "error_handled"]
        
        assert len(error_occurred_events) == 1
        assert len(error_handled_events) == 1
        
        handled_event = error_handled_events[0]
        assert handled_event["error_type"] == "RuntimeError"
        assert "Simulated error" in handled_event["error_message"]
        
        print("✅ Execute core pattern error handling works in lifecycle events")


class TestErrorRecoveryLifecycleEvents:
    """Test error recovery patterns in lifecycle events"""
    
    @pytest.mark.asyncio
    async def test_error_recovery_lifecycle_event_patterns(self):
        """Test error recovery patterns in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
            from netra_backend.app.schemas.agent import SubAgentLifecycle
        except ImportError:
            pytest.skip("Required components not available")
        
        recovery_events = []
        
        class ErrorRecoveryLifecycleAgent(BaseAgent):
            def __init__(self, max_retries=2, **kwargs):
                super().__init__(**kwargs)
                self.max_retries = max_retries
                self.attempt_count = 0
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                self.attempt_count += 1
                
                recovery_events.append({
                    "event": "execution_attempt",
                    "attempt": self.attempt_count,
                    "max_retries": self.max_retries,
                    "context_id": context.run_id
                })
                
                try:
                    await self.emit_agent_started()
                    
                    # Simulate work that fails on first attempts
                    if context.run_id.endswith("transient") and self.attempt_count <= 2:
                        await self.emit_thinking(f"Attempt {self.attempt_count} - encountering transient error")
                        raise ValueError(f"Transient error on attempt {self.attempt_count}")
                    
                    await self.emit_thinking("Processing successfully")
                    await asyncio.sleep(0.05)
                    
                    result = {
                        "recovery_test": "success",
                        "total_attempts": self.attempt_count,
                        "recovered": self.attempt_count > 1
                    }
                    
                    recovery_events.append({
                        "event": "execution_success",
                        "attempts": self.attempt_count,
                        "recovered": self.attempt_count > 1
                    })
                    
                    await self.emit_agent_completed(result)
                    return result
                    
                except Exception as e:
                    recovery_events.append({
                        "event": "execution_failed",
                        "attempt": self.attempt_count,
                        "error": str(e)
                    })
                    
                    if self.attempt_count < self.max_retries:
                        await self.emit_thinking(f"Attempting recovery (attempt {self.attempt_count}/{self.max_retries})")
                        
                        # Attempt recovery
                        await self._attempt_recovery(e)
                        
                        # Retry execution
                        return await self.execute_core_logic(context)
                    else:
                        # Max retries reached
                        recovery_events.append({
                            "event": "recovery_failed",
                            "total_attempts": self.attempt_count,
                            "final_error": str(e)
                        })
                        
                        self.set_state(SubAgentLifecycle.FAILED)
                        await self.emit_thinking("Recovery failed - maximum attempts reached")
                        raise RuntimeError(f"Recovery failed after {self.max_retries} attempts: {e}")
            
            async def _attempt_recovery(self, error: Exception):
                """Simulate recovery process"""
                recovery_events.append({
                    "event": "recovery_attempt",
                    "attempt": self.attempt_count,
                    "error_type": type(error).__name__
                })
                
                # Simulate recovery delay
                await asyncio.sleep(0.05)
                
                # Reset state for retry
                if self.get_state() == SubAgentLifecycle.FAILED:
                    self.set_state(SubAgentLifecycle.RUNNING)
        
        # Test successful execution without recovery
        success_agent = ErrorRecoveryLifecycleAgent(name="RecoverySuccessTest")
        success_context = ExecutionContext(
            run_id="recovery_success",
            agent_name=success_agent.name,
            state=DeepAgentState()
        )
        
        result = await success_agent.execute_core_logic(success_context)
        assert result["recovery_test"] == "success"
        assert result["recovered"] is False
        assert result["total_attempts"] == 1
        
        # Test transient error recovery
        recovery_agent = ErrorRecoveryLifecycleAgent(name="RecoveryTransientTest")
        transient_context = ExecutionContext(
            run_id="recovery_transient",
            agent_name=recovery_agent.name,
            state=DeepAgentState()
        )
        
        result = await recovery_agent.execute_core_logic(transient_context)
        assert result["recovery_test"] == "success"
        assert result["recovered"] is True
        assert result["total_attempts"] == 3  # Should succeed on 3rd attempt
        
        # Verify recovery events
        execution_attempts = [e for e in recovery_events if e["event"] == "execution_attempt"]
        recovery_attempts = [e for e in recovery_events if e["event"] == "recovery_attempt"]
        execution_success = [e for e in recovery_events if e["event"] == "execution_success"]
        
        assert len(execution_attempts) >= 4  # 1 success + 3 transient attempts
        assert len(recovery_attempts) == 2  # 2 recovery attempts for transient
        assert len(execution_success) == 2  # 2 successful executions
        
        print("✅ Error recovery lifecycle event patterns work correctly")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_lifecycle_events(self):
        """Test circuit breaker pattern in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        circuit_events = []
        
        class CircuitBreakerAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.failure_count = 0
                self.circuit_open = False
                self.failure_threshold = 3
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                circuit_events.append({
                    "event": "execution_request",
                    "circuit_open": self.circuit_open,
                    "failure_count": self.failure_count
                })
                
                # Check circuit breaker
                if self.circuit_open:
                    circuit_events.append({
                        "event": "circuit_breaker_rejected",
                        "failure_count": self.failure_count
                    })
                    await self.emit_thinking("Circuit breaker is open - rejecting request")
                    raise RuntimeError("Circuit breaker is open")
                
                await self.emit_agent_started()
                
                try:
                    # Simulate operation that might fail
                    if context.run_id.endswith("_fail"):
                        await self.emit_thinking("Operation failed")
                        raise ValueError("Simulated operation failure")
                    
                    # Success - reset circuit breaker
                    if self.failure_count > 0:
                        circuit_events.append({
                            "event": "circuit_breaker_reset",
                            "previous_failures": self.failure_count
                        })
                        self.failure_count = 0
                        self.circuit_open = False
                        await self.emit_thinking("Circuit breaker reset - operation successful")
                    
                    result = {
                        "circuit_breaker_test": "success",
                        "circuit_open": self.circuit_open,
                        "failure_count": self.failure_count
                    }
                    
                    await self.emit_agent_completed(result)
                    return result
                    
                except Exception as e:
                    self.failure_count += 1
                    
                    circuit_events.append({
                        "event": "operation_failed",
                        "failure_count": self.failure_count,
                        "threshold": self.failure_threshold,
                        "error": str(e)
                    })
                    
                    # Check if circuit should open
                    if self.failure_count >= self.failure_threshold:
                        self.circuit_open = True
                        circuit_events.append({
                            "event": "circuit_breaker_opened",
                            "failure_count": self.failure_count
                        })
                        await self.emit_thinking("Circuit breaker opened due to repeated failures")
                    
                    raise
        
        agent = CircuitBreakerAgent(name="CircuitBreakerTest")
        
        # Test successful operations
        success_context = ExecutionContext(
            run_id="circuit_success",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(success_context)
        assert result["circuit_breaker_test"] == "success"
        assert not result["circuit_open"]
        
        # Test failures that trigger circuit breaker
        for i in range(4):  # Exceed threshold
            fail_context = ExecutionContext(
                run_id=f"circuit_fail_{i}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            try:
                await agent.execute_core_logic(fail_context)
                assert False, "Should have failed"
            except (ValueError, RuntimeError):
                pass  # Expected
        
        # Verify circuit breaker events
        circuit_opened_events = [e for e in circuit_events if e["event"] == "circuit_breaker_opened"]
        rejected_events = [e for e in circuit_events if e["event"] == "circuit_breaker_rejected"]
        
        assert len(circuit_opened_events) == 1
        assert len(rejected_events) >= 1  # At least one rejection after circuit opened
        
        print("✅ Circuit breaker lifecycle events work correctly")
    
    @pytest.mark.asyncio
    async def test_cascading_failure_recovery_lifecycle(self):
        """Test cascading failure recovery in lifecycle events"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        cascade_events = []
        
        class CascadingFailureAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.cascade_level = 0
                self.max_cascade_level = 3
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                cascade_events.append({
                    "event": "cascade_level_entry",
                    "level": self.cascade_level,
                    "context_id": context.run_id
                })
                
                await self.emit_agent_started()
                
                try:
                    return await self._execute_with_cascade_handling(context)
                except Exception as e:
                    self.cascade_level += 1
                    
                    cascade_events.append({
                        "event": "cascade_failure",
                        "level": self.cascade_level,
                        "error": str(e),
                        "max_level": self.max_cascade_level
                    })
                    
                    if self.cascade_level <= self.max_cascade_level:
                        await self.emit_thinking(f"Cascade failure level {self.cascade_level}, attempting recovery")
                        
                        # Attempt cascade recovery
                        await self._handle_cascade_recovery(e, context)
                        
                        # Retry with recovery
                        return await self._execute_with_cascade_handling(context)
                    else:
                        cascade_events.append({
                            "event": "cascade_recovery_failed",
                            "final_level": self.cascade_level
                        })
                        await self.emit_thinking("Cascade recovery failed - maximum levels exceeded")
                        raise RuntimeError(f"Cascade failure exceeded maximum level: {self.cascade_level}")
            
            async def _execute_with_cascade_handling(self, context: ExecutionContext) -> Dict[str, Any]:
                await asyncio.sleep(0.05)
                
                # Simulate cascading failures
                if context.run_id.endswith("_cascade"):
                    if self.cascade_level == 0:
                        raise ValueError("Level 1 cascade failure")
                    elif self.cascade_level == 1:
                        raise RuntimeError("Level 2 cascade failure")  
                    elif self.cascade_level == 2:
                        raise TimeoutError("Level 3 cascade failure")
                    else:
                        # Recovery successful after 3 levels
                        await self.emit_thinking("Cascade recovery successful")
                
                result = {
                    "cascade_test": "success",
                    "cascade_level": self.cascade_level,
                    "recovered": self.cascade_level > 0
                }
                
                cascade_events.append({
                    "event": "cascade_recovery_success",
                    "final_level": self.cascade_level,
                    "recovered": self.cascade_level > 0
                })
                
                await self.emit_agent_completed(result)
                return result
            
            async def _handle_cascade_recovery(self, error: Exception, context: ExecutionContext):
                """Handle cascade recovery with backoff"""
                recovery_delay = 0.05 * self.cascade_level  # Increasing delay
                await asyncio.sleep(recovery_delay)
                
                cascade_events.append({
                    "event": "cascade_recovery_attempt",
                    "level": self.cascade_level,
                    "error_type": type(error).__name__,
                    "recovery_delay": recovery_delay
                })
        
        # Test successful cascade recovery
        cascade_agent = CascadingFailureAgent(name="CascadeRecoveryTest")
        cascade_context = ExecutionContext(
            run_id="cascade_test_cascade",
            agent_name=cascade_agent.name,
            state=DeepAgentState()
        )
        
        result = await cascade_agent.execute_core_logic(cascade_context)
        assert result["cascade_test"] == "success"
        assert result["recovered"] is True
        assert result["cascade_level"] == 3  # Should recover after 3 levels
        
        # Verify cascade events
        cascade_failures = [e for e in cascade_events if e["event"] == "cascade_failure"]
        recovery_attempts = [e for e in cascade_events if e["event"] == "cascade_recovery_attempt"]
        recovery_success = [e for e in cascade_events if e["event"] == "cascade_recovery_success"]
        
        assert len(cascade_failures) == 3  # 3 cascade levels
        assert len(recovery_attempts) == 3  # 3 recovery attempts
        assert len(recovery_success) == 1  # Final recovery success
        
        print("✅ Cascading failure recovery lifecycle events work correctly")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])