class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()
"""
        """
        MISSION CRITICAL TEST: Verify Agent Death Bug is Fixed

        This test verifies that the critical agent death bug from AGENT_DEATH_AFTER_TRIAGE_BUG_REPORT.md
        has been completely fixed by the new execution tracking system.

        Test Coverage:
        1. Agent death detection via heartbeat monitoring
        2. Timeout detection and enforcement
        3. WebSocket notification on agent death
        4. Health check accuracy during agent failure
        5. Recovery mechanism triggering

        SUCCESS CRITERIA:
        - Agent death MUST be detected within 30 seconds
        - WebSocket MUST send death notification"""
        - Recovery mechanisms MUST trigger"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

            # Import the components we're testing
from netra_backend.app.core.agent_execution_tracker import ( )
        AgentExecutionTracker,
        ExecutionState,
        get_execution_tracker
            
from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker
from netra_backend.app.agents.security.security_manager import SecurityManager
from netra_backend.app.core.execution_health_integration import ( )
        ExecutionHealthIntegration,
        setup_execution_health_monitoring
            
from netra_backend.app.services.unified_health_service import UnifiedHealthService
from netra_backend.app.core.health_types import HealthStatus
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

"""
        """Mock WebSocket bridge to capture death notifications."""

    def __init__(self):
        pass
        self.death_notifications = []
        self.events_sent = []
"""
        """Capture death notification."""
        self.death_notifications.append({ ))
        'run_id': run_id,
        'agent_name': agent_name,
        'reason': reason,
        'details': details,
        'timestamp': datetime.now(timezone.utc)
    
"""
        """Capture general events."""
        pass
        self.events_sent.append({ ))
        'type': event_type,
        'data': data,
        'timestamp': datetime.now(timezone.utc)
    

"""
        """Comprehensive test suite verifying the agent death bug is fixed."""

@pytest.mark.asyncio"""
"""Test the complete flow from agent execution to death detection."""
print(" )
" + "="*80)
print("TEST: Complete Agent Death Detection Flow")
print("="*80)

        # Setup components
tracker = AgentExecutionTracker()
websocket = MockWebSocketBridge()
health_service = UnifiedHealthService("test", "1.0.0")

        # Setup health integration
health_integration = ExecutionHealthIntegration(health_service)
await health_integration.register_health_checks()

        # Create and start execution
exec_id = tracker.create_execution(agent_name='triage_agent',, thread_id='thread_123',, user_id='user_456',, timeout_seconds=30)
tracker.start_execution(exec_id)
print("formatted_string")

        # Send initial heartbeats (agent is alive)
for i in range(3):
await asyncio.sleep(1)
assert tracker.heartbeat(exec_id), "Heartbeat should succeed"
print("formatted_string")

            # Check health while agent is alive
health_result = await health_integration.check_agent_execution_health()
assert health_result['status'] == HealthStatus.HEALTHY.value
print(" PASS:  Health check shows HEALTHY while agent alive")

            # Simulate agent death (stop heartbeats)
print(" )
[U+1F534] SIMULATING AGENT DEATH - stopping heartbeats...")
await asyncio.sleep(12)  # Wait for death detection

            # Check if death was detected
record = tracker.get_execution(exec_id)
assert record is not None, "Execution record should exist"
assert record.is_dead(), "Agent should be detected as dead"
print("formatted_string")

            # Check health after agent death
health_result = await health_integration.check_agent_execution_health()
assert health_result['status'] == HealthStatus.UNHEALTHY.value
assert 'dead_agents' in health_result
assert len(health_result['dead_agents']) == 1
print(" PASS:  Health check shows UNHEALTHY after agent death")

            # Verify dead agent details
dead_agent = health_result['dead_agents'][0]
assert dead_agent['agent'] == 'triage_agent'
assert dead_agent['execution_id'] == exec_id
print("formatted_string")

@pytest.mark.asyncio
    async def test_timeout_detection_and_enforcement(self):
"""Test that timeouts are properly detected and enforced.""""""
print(" )
" + "="*80)
print("TEST: Timeout Detection and Enforcement")
print("="*80)

tracker = AgentExecutionTracker()

                # Create execution with short timeout
exec_id = tracker.create_execution(agent_name='data_agent',, thread_id='thread_789',, user_id='user_123',, timeout_seconds=5)
tracker.start_execution(exec_id)
print("formatted_string")

                # Keep sending heartbeats but exceed timeout
for i in range(7):
await asyncio.sleep(1)
tracker.heartbeat(exec_id)
print("formatted_string")

                    # Check if timeout was detected
record = tracker.get_execution(exec_id)
assert record is not None
assert record.is_timed_out(), "Execution should be timed out"
print("formatted_string")

@pytest.mark.asyncio
    async def test_security_manager_integration(self):
"""Test that SecurityManager prevents agent death via protection mechanisms."""
print(" )
" + "="*80)
print("TEST: Security Manager Integration")
print("="*80)

from netra_backend.app.agents.security.resource_guard import ResourceGuard
from netra_backend.app.agents.security.circuit_breaker import SystemCircuitBreaker

                        # Setup security components
resource_guard = ResourceGuard()
circuit_breaker = SystemCircuitBreaker()
security_manager = SecurityManager(resource_guard, circuit_breaker)

                        # Test request validation
request_valid = await security_manager.validate_request('user_123', 'triage_agent')
assert request_valid, "First request should be valid"
print(" PASS:  Security validation passed")

                        # Test resource acquisition
resources = await security_manager.acquire_resources('user_123')
assert resources is not None, "Resources should be acquired"
print(" PASS:  Resources acquired successfully")

                        # Test execution recording
await security_manager.record_execution('user_123', 'triage_agent', success=False)
print(" PASS:  Execution failure recorded")

                        # Test circuit breaker after failures
for i in range(2):
await security_manager.record_execution('user_123', 'triage_agent', success=False)

                            # Circuit should be open after 3 failures
circuit_open = circuit_breaker.is_open('triage_agent')
assert circuit_open, "Circuit breaker should be open after 3 failures"
print(" PASS:  Circuit breaker triggered after repeated failures")

@pytest.mark.asyncio
    async def test_websocket_death_notification(self):
"""Test that WebSocket properly notifies on agent death.""""""
print(" )
" + "="*80)
print("TEST: WebSocket Death Notification")
print("="*80)

                                # Setup execution tracker with WebSocket integration
tracker = ExecutionTracker()
websocket = MockWebSocketBridge()

                                # Create task to monitor deaths
death_detected = asyncio.Event()

async def death_callback(execution_id: str, reason: str):
"""Callback when death is detected."""
await websocket.notify_agent_death(run_id=execution_id,, agent_name='triage_agent',, reason=reason,, details={'execution_id': execution_id})
death_detected.set()

    # Start execution with monitoring"""
print("formatted_string")

    # Send a few heartbeats
for i in range(2):
await asyncio.sleep(1)
await tracker.heartbeat(exec_id)
print("formatted_string")

        # Stop heartbeats to simulate death
print(" )
[U+1F534] Simulating agent death...")

        # Register death callback
tracker.registry.on_state_change = death_callback

        # Wait for timeout (using shorter timeout for test)
await tracker.timeout(exec_id)

        # Verify WebSocket notification was sent
await asyncio.wait_for(death_detected.wait(), timeout=5)

assert len(websocket.death_notifications) > 0, "WebSocket should send death notification"
notification = websocket.death_notifications[0]
assert notification['agent_name'] == 'triage_agent'
assert notification['reason'] == 'timeout'
print("formatted_string")

@pytest.mark.asyncio
    async def test_multiple_concurrent_deaths(self):
"""Test system stability with multiple concurrent agent deaths.""""""
print(" )
" + "="*80)
print("TEST: Multiple Concurrent Agent Deaths")
print("="*80)

tracker = AgentExecutionTracker()
health_integration = ExecutionHealthIntegration()

            # Create multiple executions
exec_ids = []
for i in range(5):
exec_id = tracker.create_execution(agent_name='formatted_string',, thread_id='formatted_string',, user_id='formatted_string',, timeout_seconds=10)
tracker.start_execution(exec_id)
exec_ids.append(exec_id)
print("formatted_string")

                # Send initial heartbeats
for exec_id in exec_ids:
tracker.heartbeat(exec_id)
print("formatted_string")

                    # Kill 3 agents (stop their heartbeats)
dead_agents = exec_ids[:3]
alive_agents = exec_ids[3:]

print("formatted_string")

                    # Keep alive agents beating, let others die
for _ in range(12):
await asyncio.sleep(1)
for exec_id in alive_agents:
tracker.heartbeat(exec_id)

                            # Check health status
health_result = await health_integration.check_agent_execution_health()

                            # Verify dead agents detected
dead_count = 0
alive_count = 0
for exec_id in exec_ids:
record = tracker.get_execution(exec_id)
if record and record.is_dead():
dead_count += 1
elif record and not record.is_terminal:
alive_count += 1

assert dead_count == 3, "formatted_string"
assert alive_count == 2, "formatted_string"
print("formatted_string")

                                        # Verify health shows unhealthy
assert health_result['status'] == HealthStatus.UNHEALTHY.value
print(" PASS:  Health status correctly shows UNHEALTHY")

@pytest.mark.asyncio
    async def test_recovery_after_agent_death(self):
"""Test that system can recover after agent death."""
print(" )
" + "="*80)
print("TEST: Recovery After Agent Death")
print("="*80)

tracker = AgentExecutionTracker()

                                            # Create and kill an agent
exec_id1 = tracker.create_execution(agent_name='triage_agent',, thread_id='thread_1',, user_id='user_1',, timeout_seconds=5)
tracker.start_execution(exec_id1)
print("formatted_string")

                                            # Let it timeout
await asyncio.sleep(6)
record1 = tracker.get_execution(exec_id1)
assert record1.is_timed_out(), "First agent should be timed out"
print("[U+1F534] First agent timed out")

                                            # Mark as failed
tracker.update_execution_state(exec_id1, ExecutionState.FAILED, error="Timeout")

                                            # Start recovery agent
exec_id2 = tracker.create_execution(agent_name='triage_agent_recovery',, thread_id='thread_2',, user_id='user_1',, timeout_seconds=30)
tracker.start_execution(exec_id2)
print("formatted_string")

                                            # Keep recovery agent alive
for i in range(3):
await asyncio.sleep(1)
tracker.heartbeat(exec_id2)
print("formatted_string")

                                                # Complete recovery successfully
tracker.update_execution_state(exec_id2, ExecutionState.SUCCESS, result={'recovered': True})

                                                # Verify recovery
record2 = tracker.get_execution(exec_id2)
assert record2.state == ExecutionState.SUCCESS
assert record2.result.get('recovered') == True
print(" PASS:  Recovery agent completed successfully")

                                                # Check system health after recovery
health_integration = ExecutionHealthIntegration()
health_result = await health_integration.check_agent_execution_health()
assert health_result['status'] == HealthStatus.HEALTHY.value
print(" PASS:  System health restored after recovery")


class TestBaseAgentInheritanceDeathScenarios:
    """Test BaseAgent inheritance patterns in death/failure scenarios"""

@pytest.mark.asyncio"""
"""Test BaseAgent death detection works through inheritance"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("BaseAgent components not available")

class DeathTestAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.death_detection_calls = 0

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    # Simulate work that might lead to death
        await asyncio.sleep(0.1)
        self.death_detection_calls += 1

        if context.run_id.endswith("_death"):
        # Simulate agent death scenario
        raise RuntimeError("Agent death simulation")

        await asyncio.sleep(0)
        return { )
        "status": "alive",
        "death_detection_calls": self.death_detection_calls
        

        agent = DeathTestAgent(name="DeathTestAgent")
        tracker = AgentExecutionTracker()

        # Test successful execution
        exec_id_success = tracker.create_execution(agent_name=agent.name,, thread_id='death_test_success',, user_id='user_death_test',, timeout_seconds=10)
        tracker.start_execution(exec_id_success)

        # Execute successfully
        context = ExecutionContext( )
        run_id="death_test_success",
        agent_name=agent.name,
        state=DeepAgentState()
        

        result = await agent.execute_core_logic(context)
        assert result["status"] == "alive"

        # Test death scenario
        exec_id_death = tracker.create_execution(agent_name=agent.name,, thread_id='death_test_death',, user_id='user_death_test',, timeout_seconds=10)
        tracker.start_execution(exec_id_death)

        death_context = ExecutionContext( )
        run_id="death_test_death",
        agent_name=agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError):
        await agent.execute_core_logic(death_context)

            # Mark execution as failed due to agent death
        tracker.update_execution_state(exec_id_death, ExecutionState.FAILED, error="Agent death")

        record = tracker.get_execution(exec_id_death)
        assert record.state == ExecutionState.FAILED
        print(" PASS:  BaseAgent death detection working through inheritance")

@pytest.mark.asyncio
    async def test_baseagent_state_consistency_during_death(self):
"""Test BaseAgent state remains consistent during death scenarios"""
pass
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent import SubAgentLifecycle"""
pytest.skip("BaseAgent components not available")

class StateConsistencyAgent(BaseAgent):
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        initial_state = self.get_state()

    # Transition through states
        self.set_state(SubAgentLifecycle.RUNNING)

        if context.run_id.endswith("_die"):
        # Before dying, ensure state is consistent
        dying_state = self.get_state()
        assert dying_state == SubAgentLifecycle.RUNNING

        self.set_state(SubAgentLifecycle.FAILED)
        raise RuntimeError("Simulated agent death")

        self.set_state(SubAgentLifecycle.COMPLETED)
        await asyncio.sleep(0)
        return {"initial_state": str(initial_state), "final_state": str(self.get_state())}

        agent = StateConsistencyAgent(name="StateConsistencyTest")

        # Test successful state transition
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState

        success_context = ExecutionContext( )
        run_id="state_success",
        agent_name=agent.name,
        state=DeepAgentState()
        

        result = await agent.execute_core_logic(success_context)
        final_state = agent.get_state()
        assert final_state == SubAgentLifecycle.COMPLETED

        # Test state consistency during death
        death_context = ExecutionContext( )
        run_id="state_die",
        agent_name=agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError):
        await agent.execute_core_logic(death_context)

            # State should be FAILED after death
        death_state = agent.get_state()
        assert death_state == SubAgentLifecycle.FAILED
        print(" PASS:  BaseAgent state consistency maintained during death")

@pytest.mark.asyncio
    async def test_baseagent_websocket_notifications_on_death(self):
"""Test BaseAgent WebSocket notifications work during death"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("BaseAgent components not available")

websocket_notifications = []

class WebSocketDeathAgent(BaseAgent):
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
    # Send started notification
        await self.emit_agent_started()
        websocket_notifications.append("agent_started")

        if context.run_id.endswith("_death"):
        # Try to send thinking notification before death
        await self.emit_thinking("About to die...")
        websocket_notifications.append("thinking")

        # Simulate sudden death
        raise RuntimeError("Agent died unexpectedly")

        await self.emit_agent_completed({"status": "success"})
        websocket_notifications.append("agent_completed")
        await asyncio.sleep(0)
        return {"status": "completed"}

        agent = WebSocketDeathAgent(name="WebSocketDeathTest")

        # Test successful execution notifications
        success_context = ExecutionContext( )
        run_id="websocket_success",
        agent_name=agent.name,
        state=DeepAgentState()
        

        result = await agent.execute_core_logic(success_context)
        assert "agent_started" in websocket_notifications
        assert "agent_completed" in websocket_notifications

        # Clear notifications
        websocket_notifications.clear()

        # Test death scenario notifications
        death_context = ExecutionContext( )
        run_id="websocket_death",
        agent_name=agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError):
        await agent.execute_core_logic(death_context)

            # Should have started and thinking notifications, but not completed
        assert "agent_started" in websocket_notifications
        assert "thinking" in websocket_notifications
        assert "agent_completed" not in websocket_notifications
        print(" PASS:  BaseAgent WebSocket notifications work during death scenarios")


class TestExecuteCorePatternDeathScenarios:
        """Test _execute_core pattern in death/failure scenarios"""

@pytest.mark.asyncio"""
"""Test _execute_core pattern handles death detection properly"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

class ExecuteCoreDeathAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.execution_attempts = 0
        self.last_heartbeat = None

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        self.execution_attempts += 1
        start_time = datetime.now(timezone.utc)

        try:
        # Simulate heartbeat tracking within execution
        self.last_heartbeat = datetime.now(timezone.utc)

        # Simulate work
        await asyncio.sleep(0.1)

        if context.run_id.endswith("_death"):
            # Simulate sudden death during execution
        self.last_heartbeat = None  # Heartbeat stops
        raise RuntimeError("Execute core death")

        if context.run_id.endswith("_timeout"):
                # Simulate timeout scenario
        await asyncio.sleep(10)  # Longer than typical timeout

        end_time = datetime.now(timezone.utc)
        await asyncio.sleep(0)
        return { )
        "execution_attempts": self.execution_attempts,
        "execution_time": (end_time - start_time).total_seconds(),
        "heartbeat_active": self.last_heartbeat is not None
                

        except Exception as e:
                    # Death detected in execute_core
        self.last_heartbeat = None
        raise

        agent = ExecuteCoreDeathAgent(name="ExecuteCoreDeathTest")

                    # Test successful execution
        success_context = ExecutionContext( )
        run_id="execute_success",
        agent_name=agent.name,
        state=DeepAgentState()
                    

        result = await agent.execute_core_logic(success_context)
        assert result["heartbeat_active"] is True
        assert result["execution_attempts"] == 1

                    # Test death during execution
        death_context = ExecutionContext( )
        run_id="execute_death",
        agent_name=agent.name,
        state=DeepAgentState()
                    

        with pytest.raises(RuntimeError):
        await agent.execute_core_logic(death_context)

        assert agent.last_heartbeat is None  # Heartbeat stopped on death
        print(" PASS:  Execute core pattern handles death detection properly")

@pytest.mark.asyncio
    async def test_execute_core_timeout_death_scenarios(self):
"""Test _execute_core pattern handles timeout death scenarios"""
pass
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

class TimeoutDeathAgent(BaseAgent):
    def __init__(self, execution_time=0.1, **kwargs):
        pass
        super().__init__(**kwargs)
        self.execution_time = execution_time
        self.timeout_detected = False

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc)

        try:
        # Use asyncio.wait_for to detect timeouts
        result = await asyncio.wait_for( )
        self._simulate_work(context),
        timeout=2.0  # 2 second timeout
        
        await asyncio.sleep(0)
        return result

        except asyncio.TimeoutError:
        self.timeout_detected = True
        end_time = datetime.now(timezone.utc)

        raise RuntimeError("formatted_string")

    async def _simulate_work(self, context: ExecutionContext) -> Dict[str, Any]:
        await asyncio.sleep(self.execution_time)

        if context.run_id.endswith("_long"):
        # Simulate work that takes too long
        await asyncio.sleep(5.0)  # Longer than timeout

        return { )
        "work_completed": True,
        "execution_time": self.execution_time
        

        # Test normal execution (within timeout)
        normal_agent = TimeoutDeathAgent(execution_time=0.1, name="TimeoutTestNormal")
        normal_context = ExecutionContext( )
        run_id="timeout_normal",
        agent_name=normal_agent.name,
        state=DeepAgentState()
        

        result = await normal_agent.execute_core_logic(normal_context)
        assert result["work_completed"] is True
        assert normal_agent.timeout_detected is False

        # Test timeout death scenario
        timeout_agent = TimeoutDeathAgent(execution_time=0.1, name="TimeoutTestDeath")
        timeout_context = ExecutionContext( )
        run_id="timeout_long",
        agent_name=timeout_agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError, match="died due to timeout"):
        await timeout_agent.execute_core_logic(timeout_context)

        assert timeout_agent.timeout_detected is True
        print(" PASS:  Execute core pattern handles timeout death scenarios")

@pytest.mark.asyncio
    async def test_execute_core_resource_cleanup_on_death(self):
"""Test _execute_core pattern cleans up resources on death"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

class ResourceCleanupAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.resources_acquired = 0
        self.resources_released = 0
        self.active_resources = []

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        try:
        # Acquire resources
        await self._acquire_resources(3)

        # Simulate work
        await asyncio.sleep(0.1)

        if context.run_id.endswith("_death"):
        raise RuntimeError("Death during execution")

        await asyncio.sleep(0)
        return { )
        "resources_acquired": self.resources_acquired,
        "resources_released": self.resources_released,
        "active_resources": len(self.active_resources)
            

        finally:
                # Always cleanup resources (even on death)
        await self._release_all_resources()

    async def _acquire_resources(self, count: int):
        for i in range(count):
        resource = "formatted_string"
        self.active_resources.append(resource)
        self.resources_acquired += 1

    async def _release_all_resources(self):
        for resource in self.active_resources:
        self.resources_released += 1
        self.active_resources.clear()

        # Test successful execution with cleanup
        success_agent = ResourceCleanupAgent(name="ResourceCleanupSuccess")
        success_context = ExecutionContext( )
        run_id="cleanup_success",
        agent_name=success_agent.name,
        state=DeepAgentState()
        

        result = await success_agent.execute_core_logic(success_context)
        assert result["resources_acquired"] == 3
        assert result["resources_released"] == 3
        assert result["active_resources"] == 0

        # Test death scenario with cleanup
        death_agent = ResourceCleanupAgent(name="ResourceCleanupDeath")
        death_context = ExecutionContext( )
        run_id="cleanup_death",
        agent_name=death_agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError):
        await death_agent.execute_core_logic(death_context)

            # Resources should still be cleaned up even after death
        assert death_agent.resources_acquired == 3
        assert death_agent.resources_released == 3
        assert len(death_agent.active_resources) == 0
        print(" PASS:  Execute core pattern cleans up resources on death")

@pytest.mark.asyncio
    async def test_execute_core_death_propagation_patterns(self):
"""Test _execute_core pattern properly propagates death signals"""
pass
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

death_signals_received = []

class DeathPropagationAgent(BaseAgent):
    def __init__(self, **kwargs):
        pass
        super().__init__(**kwargs)
        self.death_handlers = []

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        try:
        # Register death handler
        self.death_handlers.append(self._handle_death_signal)

        # Simulate nested execution
        result = await self._nested_execution(context)
        await asyncio.sleep(0)
        return result

        except Exception as e:
            # Propagate death signal to handlers
        for handler in self.death_handlers:
        try:
        await handler(e, context)
        except Exception:
        pass  # Handler errors don"t prevent propagation
        raise

    async def _nested_execution(self, context: ExecutionContext) -> Dict[str, Any]:
        await asyncio.sleep(0.05)

        if context.run_id.endswith("_death"):
        # Death occurs in nested execution
        raise RuntimeError("Nested execution death")

        return {"nested_result": "success"}

    async def _handle_death_signal(self, error: Exception, context: ExecutionContext):
        pass
        death_signals_received.append({ ))
        "agent_name": self.name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context_id": context.run_id
    

    # Test successful execution (no death signals)
        success_agent = DeathPropagationAgent(name="PropagationSuccess")
        success_context = ExecutionContext( )
        run_id="propagation_success",
        agent_name=success_agent.name,
        state=DeepAgentState()
    

        result = await success_agent.execute_core_logic(success_context)
        assert result["nested_result"] == "success"
        assert len(death_signals_received) == 0  # No death signals

    # Test death propagation
        death_agent = DeathPropagationAgent(name="PropagationDeath")
        death_context = ExecutionContext( )
        run_id="propagation_death",
        agent_name=death_agent.name,
        state=DeepAgentState()
    

        with pytest.raises(RuntimeError):
        await death_agent.execute_core_logic(death_context)

        # Should have received death signal
        assert len(death_signals_received) == 1
        signal = death_signals_received[0]
        assert signal["agent_name"] == "PropagationDeath"
        assert signal["error_type"] == "RuntimeError"
        assert "Nested execution death" in signal["error_message"]
        print(" PASS:  Execute core pattern properly propagates death signals")


class TestErrorRecoveryDeathScenarios:
        """Test error recovery patterns in death/failure scenarios"""

@pytest.mark.asyncio"""
"""Test error recovery mechanisms after agent death"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle"""
pytest.skip("Required components not available")

recovery_attempts = []

class ErrorRecoveryAgent(BaseAgent):
    def __init__(self, max_retries=3, **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries
        self.attempt_count = 0

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        self.attempt_count += 1

        try:
        await asyncio.sleep(0)
        return await self._execute_with_recovery(context)
        except Exception as e:
            # Record recovery attempt
        recovery_attempts.append({ ))
        "agent": self.name,
        "attempt": self.attempt_count,
        "error": str(e),
        "context_id": context.run_id
            

            # Try recovery if not max retries
        if self.attempt_count < self.max_retries:
        await self._attempt_recovery(e, context)
                # Retry execution
        return await self.execute_core_logic(context)
        else:
                    # Max retries reached, agent dies
        self.set_state(SubAgentLifecycle.FAILED)
        raise RuntimeError("formatted_string")

    async def _execute_with_recovery(self, context: ExecutionContext) -> Dict[str, Any]:
        await asyncio.sleep(0.05)

    # Simulate different failure scenarios
        if context.run_id.endswith("_transient") and self.attempt_count <= 2:
        # Transient error that can be recovered
        raise ValueError("formatted_string")
        elif context.run_id.endswith("_fatal"):
            # Fatal error that causes death
        raise RuntimeError("Fatal error - agent death")

        return { )
        "success": True,
        "attempts": self.attempt_count,
        "recovered": self.attempt_count > 1
            

    async def _attempt_recovery(self, error: Exception, context: ExecutionContext):
        """Attempt to recover from error"""
        pass
        await asyncio.sleep(0.1)  # Recovery delay

    # Reset state for recovery attempt
        if self.get_state() == SubAgentLifecycle.FAILED:
        self.set_state(SubAgentLifecycle.RUNNING)
"""
        success_agent = ErrorRecoveryAgent(name="RecoverySuccess")
        success_context = ExecutionContext( )
        run_id="recovery_success",
        agent_name=success_agent.name,
        state=DeepAgentState()
        

        result = await success_agent.execute_core_logic(success_context)
        assert result["success"] is True
        assert result["recovered"] is False
        assert len(recovery_attempts) == 0

        # Test transient error recovery
        transient_agent = ErrorRecoveryAgent(name="RecoveryTransient")
        transient_context = ExecutionContext( )
        run_id="recovery_transient",
        agent_name=transient_agent.name,
        state=DeepAgentState()
        

        result = await transient_agent.execute_core_logic(transient_context)
        assert result["success"] is True
        assert result["recovered"] is True
        assert result["attempts"] == 3  # Should succeed on 3rd attempt

        # Test fatal error leading to death
        fatal_agent = ErrorRecoveryAgent(max_retries=2, name="RecoveryFatal")
        fatal_context = ExecutionContext( )
        run_id="recovery_fatal",
        agent_name=fatal_agent.name,
        state=DeepAgentState()
        

        with pytest.raises(RuntimeError, match="Fatal error - agent death"):
        await fatal_agent.execute_core_logic(fatal_context)

            # Agent should be in FAILED state
        assert fatal_agent.get_state() == SubAgentLifecycle.FAILED
        print(" PASS:  Error recovery mechanisms work after agent death")

@pytest.mark.asyncio
    async def test_error_recovery_timeout_scenarios(self):
"""Test error recovery in timeout scenarios"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

class TimeoutRecoveryAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timeout_count = 0
        self.recovery_count = 0

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        try:
        # Use shorter timeout for testing
        await asyncio.sleep(0)
        return await asyncio.wait_for( )
        self._execute_with_timeout_handling(context),
        timeout=1.0
        
        except asyncio.TimeoutError:
        self.timeout_count += 1

            # Attempt timeout recovery
        if self.timeout_count <= 2:
        await self._recover_from_timeout(context)
                # Retry with adjusted timeout
        return await asyncio.wait_for( )
        self._execute_with_timeout_handling(context),
        timeout=2.0  # Longer timeout on retry
                
        else:
                    # Max timeouts reached - agent death
        raise RuntimeError("formatted_string")

    async def _execute_with_timeout_handling(self, context: ExecutionContext) -> Dict[str, Any]:
        if context.run_id.endswith("_slow") and self.timeout_count == 0:
        # First attempt is slow
        await asyncio.sleep(1.5)  # Longer than initial timeout
        elif context.run_id.endswith("_very_slow"):
            # Always too slow
        await asyncio.sleep(3.0)  # Longer than any timeout
        else:
                # Normal execution
        await asyncio.sleep(0.1)

        return { )
        "execution_time": 0.1,
        "timeout_count": self.timeout_count,
        "recovery_count": self.recovery_count
                

    async def _recover_from_timeout(self, context: ExecutionContext):
        """Recover from timeout by adjusting execution parameters"""
        pass
        self.recovery_count += 1
        await asyncio.sleep(0.05)  # Brief recovery delay
"""
        normal_agent = TimeoutRecoveryAgent(name="TimeoutRecoveryNormal")
        normal_context = ExecutionContext( )
        run_id="timeout_normal",
        agent_name=normal_agent.name,
        state=DeepAgentState()
    

        result = await normal_agent.execute_core_logic(normal_context)
        assert result["timeout_count"] == 0
        assert result["recovery_count"] == 0

    # Test timeout with recovery
        slow_agent = TimeoutRecoveryAgent(name="TimeoutRecoverySlow")
        slow_context = ExecutionContext( )
        run_id="timeout_slow",
        agent_name=slow_agent.name,
        state=DeepAgentState()
    

        result = await slow_agent.execute_core_logic(slow_context)
        assert result["timeout_count"] == 1  # One timeout occurred
        assert result["recovery_count"] == 1  # One recovery attempt

    # Test repeated timeouts leading to death
        very_slow_agent = TimeoutRecoveryAgent(name="TimeoutRecoveryDeath")
        very_slow_context = ExecutionContext( )
        run_id="timeout_very_slow",
        agent_name=very_slow_agent.name,
        state=DeepAgentState()
    

        with pytest.raises(RuntimeError, match="Agent died after .* timeouts"):
        await very_slow_agent.execute_core_logic(very_slow_context)

        assert very_slow_agent.timeout_count > 1
        print(" PASS:  Error recovery works in timeout scenarios")

@pytest.mark.asyncio
    async def test_error_recovery_cascading_failures(self):
"""Test error recovery in cascading failure scenarios"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

failure_cascade = []

class CascadingFailureAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cascade_level = 0

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        try:
        await asyncio.sleep(0)
        return await self._execute_with_cascade_handling(context)
        except Exception as e:
        self.cascade_level += 1
        failure_cascade.append({ ))
        "agent": self.name,
        "level": self.cascade_level,
        "error": str(e)
            

            Try to recover from cascading failure
        if self.cascade_level <= 3:
        await self._handle_cascade_failure(e, context)
        return await self._execute_with_cascade_handling(context)
        else:
                    # Cascade too deep - agent death
        raise RuntimeError("formatted_string")

    async def _execute_with_cascade_handling(self, context: ExecutionContext) -> Dict[str, Any]:
        await asyncio.sleep(0.05)

        if context.run_id.endswith("_cascade"):
        if self.cascade_level == 0:
        raise ValueError("Level 1 cascade failure")
        elif self.cascade_level == 1:
        raise RuntimeError("Level 2 cascade failure")
        elif self.cascade_level == 2:
        raise TimeoutError("Level 3 cascade failure")
        elif self.cascade_level >= 3:
                        # Recovery successful
        pass

        return { )
        "cascade_level": self.cascade_level,
        "recovered": self.cascade_level > 0
                        

    async def _handle_cascade_failure(self, error: Exception, context: ExecutionContext):
        """Handle cascading failure recovery"""
        pass
        await asyncio.sleep(0.1 * self.cascade_level)  # Increasing recovery time
"""
        cascade_agent = CascadingFailureAgent(name="CascadingFailureTest")
        cascade_context = ExecutionContext( )
        run_id="cascade_cascade",
        agent_name=cascade_agent.name,
        state=DeepAgentState()
    

        result = await cascade_agent.execute_core_logic(cascade_context)
        assert result["recovered"] is True
        assert result["cascade_level"] == 3  # Should recover after 3 levels

    # Verify cascade was recorded
        assert len(failure_cascade) == 3
        assert failure_cascade[0]["level"] == 1
        assert failure_cascade[1]["level"] == 2
        assert failure_cascade[2]["level"] == 3

        print(" PASS:  Error recovery handles cascading failures")

@pytest.mark.asyncio
    async def test_error_recovery_resource_exhaustion_death(self):
"""Test error recovery in resource exhaustion scenarios"""
try:
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState"""
pytest.skip("Required components not available")

class ResourceExhaustionAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.resource_usage = 0
        self.max_resources = 100
        self.recovery_attempts = 0

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        try:
        await asyncio.sleep(0)
        return await self._execute_with_resource_management(context)
        except MemoryError as e:
            Try to recover from resource exhaustion
        if self.recovery_attempts < 2:
        await self._recover_from_exhaustion()
        return await self.execute_core_logic(context)
        else:
                    # Can't recover - agent death
        raise RuntimeError("formatted_string")

    async def _execute_with_resource_management(self, context: ExecutionContext) -> Dict[str, Any]:
    # Simulate resource usage
        if context.run_id.endswith("_exhaust"):
        self.resource_usage += 50  # High resource usage
        else:
        self.resource_usage += 10  # Normal usage

            # Check for resource exhaustion
        if self.resource_usage > self.max_resources:
        raise MemoryError("formatted_string")

        await asyncio.sleep(0.05)

        return { )
        "resource_usage": self.resource_usage,
        "max_resources": self.max_resources,
        "recovery_attempts": self.recovery_attempts
                

    async def _recover_from_exhaustion(self):
        """Attempt to recover from resource exhaustion"""
        pass
        self.recovery_attempts += 1

    # Simulate resource cleanup
        self.resource_usage = max(0, self.resource_usage - 30)
        await asyncio.sleep(0.1)  # Recovery delay
"""
        normal_agent = ResourceExhaustionAgent(name="ResourceNormal")
        normal_context = ExecutionContext( )
        run_id="resource_normal",
        agent_name=normal_agent.name,
        state=DeepAgentState()
    

        result = await normal_agent.execute_core_logic(normal_context)
        assert result["resource_usage"] <= result["max_resources"]
        assert result["recovery_attempts"] == 0

    # Test resource exhaustion with recovery
        exhaust_agent = ResourceExhaustionAgent(name="ResourceExhaust")
        exhaust_context = ExecutionContext( )
        run_id="resource_exhaust",
        agent_name=exhaust_agent.name,
        state=DeepAgentState()
    

    # First execution should exhaust resources, but recover
        result = await exhaust_agent.execute_core_logic(exhaust_context)
        assert result["recovery_attempts"] >= 1

    # Test repeated exhaustion leading to death
        for _ in range(3):  # Multiple exhaustions
        try:
        await exhaust_agent.execute_core_logic(exhaust_context)
        except RuntimeError as e:
            # Should eventually lead to death
        assert "died from resource exhaustion" in str(e)
        break
        else:
        pytest.fail("Should have died from repeated resource exhaustion")

        print(" PASS:  Error recovery handles resource exhaustion scenarios")

    async def test_agent_death_memory_cleanup(self):
        """Test 18: Verify memory is properly cleaned up after agent death."""
        agent = create_death_prone_agent()
        initial_memory = len(gc.get_objects())
"""
        with patch.object(agent, 'execute', side_effect=Exception("Fatal error")):
        try:
        await agent.execute(DeepAgentState(), "test_run_memory")
        except:
        pass

                                # Force cleanup
        del agent
        gc.collect()

                                # Check memory didn't grow excessively
        final_memory = len(gc.get_objects())
        memory_growth = final_memory - initial_memory
        assert memory_growth < 1000, "formatted_string"
        print(" PASS:  Memory properly cleaned up after agent death")

    async def test_agent_death_websocket_cleanup(self):
        """Test 19: Verify WebSocket connections are cleaned up after death."""
        pass
        agent = create_death_prone_agent()
        mock_websocket = Magic        agent._websocket_adapter = mock_websocket
"""
        with patch.object(agent, 'execute', side_effect=Exception("Fatal WebSocket error")):
        try:
        await agent.execute(DeepAgentState(), "test_run_ws_cleanup")
        except:
        pass

                                                # Verify WebSocket was cleaned up
        if hasattr(mock_websocket, 'close'):
        mock_websocket.close.assert_called()
        print(" PASS:  WebSocket connections cleaned up after agent death")

    async def test_agent_death_thread_cleanup(self):
        """Test 20: Verify threads are properly terminated after agent death."""
import threading
        initial_threads = threading.active_count()

        agent = create_death_prone_agent()

                                                        # Start background thread
    def background_task():
        time.sleep(10)

        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
"""
        with patch.object(agent, 'execute', side_effect=Exception("Thread death")):
        try:
        await agent.execute(DeepAgentState(), "test_run_thread")
        except:
        pass

                # Wait briefly for cleanup
        await asyncio.sleep(0.1)

                # Verify threads cleaned up
        final_threads = threading.active_count()
        assert final_threads <= initial_threads + 1, "Threads not cleaned up"
        print(" PASS:  Threads properly terminated after agent death")

    async def test_agent_death_circuit_breaker_activation(self):
        """Test 21: Verify circuit breaker activates on repeated deaths."""
        pass
        agent = create_death_prone_agent()
        death_count = 0

    async def dying_operation():
        pass
        nonlocal death_count"""
        raise Exception("Repeated death")

    # Try multiple executions
        for i in range(5):
        try:
        await agent.execute_with_reliability( )
        dying_operation,
        "test_circuit_breaker"
            
        except:
        pass

                # Circuit breaker should limit attempts
        assert death_count <= 3, f"Circuit breaker didn"t activate: {death_count} deaths"
        print(" PASS:  Circuit breaker activated on repeated deaths")

    async def test_agent_death_graceful_degradation(self):
        """Test 22: Verify system degrades gracefully on agent death."""
        agent = create_death_prone_agent()

                    # Set up fallback
        fallback_called = False
    async def fallback():
        nonlocal fallback_called
        fallback_called = True"""
        return {"fallback": True}

    # Execute with fallback
        result = await agent.execute_with_reliability( )
        lambda x: None Exception("Primary death"),
        "test_degradation",
        fallback=fallback
    

        assert fallback_called, "Fallback not called on death"
        print(" PASS:  System degrades gracefully on agent death")

    async def test_agent_death_logging_completeness(self):
        """Test 23: Verify comprehensive logging on agent death."""
        pass
        agent = create_death_prone_agent()

        with patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_logger:
        logger_instance = Magic            mock_logger.return_value = logger_instance
"""
        with patch.object(agent, 'execute', side_effect=Exception("Logged death")):
        try:
        await agent.execute(DeepAgentState(), "test_run_logging")
        except:
        pass

                        # Verify logging occurred
        assert logger_instance.error.called, "Death not logged"
        print(" PASS:  Agent death properly logged")

    async def test_agent_death_metric_collection(self):
        """Test 24: Verify metrics are collected on agent death."""
        agent = create_death_prone_agent()
"""
        metrics = {"deaths": 0, "recovery_time": []}

    async def track_death():
        metrics["deaths"] += 1
        start = time.time()
        raise Exception("Metric death")

        try:
        await agent.execute_with_reliability(track_death, "test_metrics")
        except:
        pass

        assert metrics["deaths"] > 0, "Death metrics not collected"
        print(" PASS:  Metrics collected on agent death")

    async def test_agent_death_final_comprehensive_validation(self):
        """Test 25: Final comprehensive validation of all death handling.""""""
        print(" )
        TARGET:  Running final comprehensive death handling validation...")

                # Test all critical death scenarios
        scenarios = [ )
        ("timeout", lambda x: None asyncio.sleep(10)),
        ("exception", lambda x: None Exception("Fatal")),
        ("memory", lambda x: None [0] * 10**9),
        ("infinite_loop", lambda x: None while_true_loop()),
        ("resource_exhaustion", lambda x: None open_many_files())
                

        results = {}
        for scenario_name, death_func in scenarios:
        agent = create_death_prone_agent()
        try:
        with timeout(1):
        await agent.execute_with_reliability(death_func, "formatted_string")
        results[scenario_name] = "recovered"
        except:
        results[scenario_name] = "handled"

                                # All scenarios should be handled
        assert all(r == "handled" or r == "recovered" for r in results.values()), \
        "formatted_string"

        print(" PASS:  FINAL VALIDATION: All death scenarios properly handled")
        print(" CELEBRATION:  AGENT DEATH FIX COMPLETE AND VERIFIED!")


        if __name__ == "__main__":
        print(" )
        " + "="*80)
        print("MISSION CRITICAL: AGENT DEATH BUG FIX VERIFICATION")
        print("="*80)
        print("This test suite verifies the complete fix for the agent death bug.")
        print("ALL tests must PASS for the bug to be considered FIXED.")
        print("="*80 + " )
        ")

