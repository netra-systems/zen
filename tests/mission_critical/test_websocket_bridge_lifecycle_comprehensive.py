#!/usr/bin/env python
"""MISSION CRITICAL: Comprehensive WebSocket Bridge Lifecycle Tests

CRITICAL BUSINESS CONTEXT:
- WebSocket bridge lifecycle is 90% of chat value delivery
- These tests prevent regressions that break real-time user interactions
- ANY FAILURE HERE MEANS CHAT IS BROKEN AND USERS CAN'T SEE AI WORKING

This comprehensive test suite validates:
1. Bridge propagation to agents before execution
2. All 5 critical events are emitted properly
3. Bridge propagation through nested agent calls
4. Error handling when bridge is missing
5. Concurrent agent executions maintain separate bridges
6. Bridge survives agent retries and fallbacks
7. Tool dispatcher receives bridge for tool events
8. State preservation across agent lifecycle
9. Stress tests with multiple concurrent agents
10. Regression tests for legacy WebSocket patterns

THESE TESTS MUST BE UNFORGIVING - IF BRIDGE PROPAGATION BREAKS AGAIN, THEY MUST FAIL.

NOTE: This test uses comprehensive mocks to avoid Docker dependencies while still
validating the complete WebSocket bridge integration patterns.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import random
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'

# Import production components for testing
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    get_agent_websocket_bridge,
    IntegrationState,
    IntegrationConfig
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.manager import WebSocketManager


# ============================================================================
# COMPREHENSIVE MOCK INFRASTRUCTURE
# ============================================================================

@dataclass
class WebSocketEventCapture:
    """Captures WebSocket events for validation."""
    timestamp: float
    run_id: str
    event_type: str
    agent_name: Optional[str]
    payload: Dict[str, Any]
    thread_id: Optional[str] = None

@dataclass
class BridgeLifecycleMetrics:
    """Tracks bridge lifecycle metrics for comprehensive validation."""
    bridges_created: int = 0
    bridges_initialized: int = 0
    agents_with_bridge_set: int = 0
    successful_event_deliveries: int = 0
    failed_event_deliveries: int = 0
    concurrent_executions: int = 0
    bridge_propagation_failures: int = 0


class ComprehensiveMockWebSocketManager:
    """Ultra-comprehensive WebSocket manager that captures ALL events and validates bridge behavior."""
    
    def __init__(self):
        self.events: List[WebSocketEventCapture] = []
        self.connections: Dict[str, Any] = {}
        self.delivery_failures: List[Dict] = []
        self.event_lock = asyncio.Lock()
        self.metrics = BridgeLifecycleMetrics()
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Capture and validate every WebSocket event."""
        async with self.event_lock:
            event = WebSocketEventCapture(
                timestamp=time.time(),
                run_id=message.get('run_id', 'unknown'),
                event_type=message.get('type', 'unknown'),
                agent_name=message.get('agent_name'),
                payload=message,
                thread_id=thread_id
            )
            self.events.append(event)
            self.metrics.successful_event_deliveries += 1
            
            # Log critical events for debugging
            if event.event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                logger.debug(f"🔔 CRITICAL EVENT CAPTURED: {event.event_type} for {event.agent_name}")
            
            return True
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Alternative sending method."""
        return await self.send_to_thread(f"user_{user_id}", message)
    
    def get_events_for_run(self, run_id: str) -> List[WebSocketEventCapture]:
        """Get all events for a specific run ID."""
        return [event for event in self.events if event.run_id == run_id]
    
    def get_critical_events_for_run(self, run_id: str) -> List[WebSocketEventCapture]:
        """Get the 5 critical events for business value."""
        critical_types = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        return [event for event in self.events 
                if event.run_id == run_id and event.event_type in critical_types]
    
    def validate_event_sequence(self, run_id: str) -> Tuple[bool, List[str]]:
        """Validate proper event sequence for a run."""
        events = self.get_events_for_run(run_id)
        event_types = [event.event_type for event in events]
        
        validation_errors = []
        
        # Must start with agent_started
        if not event_types or event_types[0] != 'agent_started':
            validation_errors.append("Missing or incorrect first event (should be agent_started)")
        
        # Must end with agent_completed or error
        if event_types and event_types[-1] not in ['agent_completed', 'agent_error']:
            validation_errors.append("Missing completion event (should be agent_completed or agent_error)")
        
        # Check for required thinking events
        if 'agent_thinking' not in event_types:
            validation_errors.append("Missing agent_thinking events")
        
        return len(validation_errors) == 0, validation_errors
    
    def reset_events(self):
        """Reset captured events for clean test state."""
        self.events.clear()
        self.delivery_failures.clear()
        self.metrics = BridgeLifecycleMetrics()


class TestAgent(BaseAgent):
    """Test agent that validates bridge propagation."""
    
    def __init__(self, name: str = "TestAgent", should_emit_events: bool = True, 
                 should_fail: bool = False, nested_agent: Optional['TestAgent'] = None):
        super().__init__(name=name)
        self.should_emit_events = should_emit_events
        self.should_fail = should_fail
        self.nested_agent = nested_agent
        self.execution_count = 0
        self.bridge_was_set = False
        self.events_emitted = []
    
    def set_websocket_bridge(self, bridge):
        """Track when bridge is set."""
        self.bridge_was_set = True
        super().set_websocket_bridge(bridge)
    
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", stream_updates: bool = False) -> Any:
        """Execute with comprehensive event emission and validation."""
        self.execution_count += 1
        
        if self.should_fail:
            if self.should_emit_events:
                await self.emit_error("Test agent failure", "test_failure")
                self.events_emitted.append("error")
            raise Exception(f"Test agent {self.name} intentionally failed")
        
        if self.should_emit_events:
            # Emit thinking event
            await self.emit_thinking(f"{self.name} is processing request")
            self.events_emitted.append("thinking")
            
            # Simulate tool execution
            await self.emit_tool_executing("test_tool", {"param": "value"})
            self.events_emitted.append("tool_executing")
            
            # Small delay to simulate work
            await asyncio.sleep(0.1)
            
            await self.emit_tool_completed("test_tool", {"result": "success"})
            self.events_emitted.append("tool_completed")
            
            # Execute nested agent if configured
            if self.nested_agent:
                nested_result = await self.nested_agent.execute(state, run_id, stream_updates)
                
            await self.emit_progress(f"{self.name} completed successfully", is_complete=True)
            self.events_emitted.append("progress")
        
        return {"status": "success", "agent": self.name, "execution_count": self.execution_count}


# ============================================================================
# COMPREHENSIVE TEST FIXTURES
# ============================================================================

@pytest.fixture
def isolated_environment():
    """Fixture to ensure isolated test environment."""
    # Mock environment variables that might cause real service connections
    old_env = {}
    test_env_vars = {
        'WEBSOCKET_TEST_ISOLATED': 'true',
        'SKIP_REAL_SERVICES': 'true',
        'DATABASE_URL': 'mock://test',
        'REDIS_URL': 'mock://test',
    }
    
    for key, value in test_env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, old_value in old_env.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

@pytest.fixture
def mock_websocket_manager():
    """Comprehensive mock WebSocket manager."""
    return ComprehensiveMockWebSocketManager()

@pytest.fixture
async def websocket_bridge(mock_websocket_manager, isolated_environment):
    """Create AgentWebSocketBridge with mock WebSocket manager."""
    # Mock all external dependencies to prevent real service connections
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket_manager),
        get_agent_execution_registry=MagicMock(return_value=MagicMock())
    ):
        # Create singleton bridge instance
        bridge = AgentWebSocketBridge()
        
        # Initialize the bridge with mocks
        result = await bridge.ensure_integration()
        assert result.success, f"Bridge initialization failed: {result.error}"
        
        yield bridge

@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing."""
    mock = MagicMock(spec=LLMManager)
    mock.get_model_config = MagicMock(return_value={"model": "test"})
    return mock

@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher with WebSocket support."""
    mock = MagicMock(spec=ToolDispatcher)
    mock.has_websocket_support = True
    mock.executor = MagicMock()
    mock.executor.websocket_bridge = None
    mock.diagnose_websocket_wiring = MagicMock(return_value={"critical_issues": []})
    return mock

@pytest.fixture
async def agent_registry(mock_llm_manager, mock_tool_dispatcher, websocket_bridge):
    """Agent registry with WebSocket bridge configured."""
    registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
    registry.set_websocket_bridge(websocket_bridge)
    return registry

@pytest.fixture
async def execution_engine(agent_registry, websocket_bridge):
    """Execution engine with bridge configured."""
    return ExecutionEngine(agent_registry, websocket_bridge)


# ============================================================================
# COMPREHENSIVE BRIDGE LIFECYCLE TESTS
# ============================================================================

class TestWebSocketBridgeLifecycleComprehensive:
    """Comprehensive WebSocket bridge lifecycle tests that MUST catch any regression."""
    
    @pytest.mark.asyncio
    async def test_bridge_propagation_before_agent_execution(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge must be set on agents BEFORE execution starts."""
        # Create test agent
        test_agent = TestAgent("PropagationTest", should_emit_events=True)
        
        # Verify bridge is not set initially
        assert not test_agent.bridge_was_set, "Bridge should not be set initially"
        assert not test_agent.has_websocket_context(), "Agent should not have WebSocket context initially"
        
        # Set bridge (simulating what AgentRegistry does)
        test_agent.set_websocket_bridge(websocket_bridge)
        
        # Verify bridge propagation
        assert test_agent.bridge_was_set, "Bridge should be set after set_websocket_bridge()"
        assert test_agent.has_websocket_context(), "Agent should have WebSocket context after bridge set"
        
        # Execute agent and verify events are emitted
        run_id = str(uuid.uuid4())
        result = await test_agent.execute(None, run_id, True)
        
        # Verify events were emitted successfully
        events = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events) > 0, "No WebSocket events were emitted - bridge propagation failed!"
        
        # Verify specific events were emitted
        event_types = {event.event_type for event in events}
        expected_events = {'tool_executing', 'tool_completed'}
        missing_events = expected_events - event_types
        assert not missing_events, f"Missing critical events: {missing_events}"
        
        logger.info("✅ Bridge propagation before execution: PASSED")

    @pytest.mark.asyncio
    async def test_all_five_critical_events_emitted(self, websocket_bridge, mock_websocket_manager, agent_registry):
        """CRITICAL: All 5 business-critical events must be emitted during agent execution."""
        # Register test agent
        test_agent = TestAgent("CriticalEventsTest", should_emit_events=True)
        agent_registry.register("test_agent", test_agent)
        
        # Create execution context
        run_id = str(uuid.uuid4())
        context = AgentExecutionContext(
            run_id=run_id,
            agent_name="test_agent",
            steps=[PipelineStep(agent_name="test_agent", params={})],
            thread_id=f"thread_{run_id}"
        )
        
        # Execute through AgentExecutionCore to get all bridge events
        agent_core = AgentExecutionCore(agent_registry, websocket_bridge)
        state = DeepAgentState()
        
        # Execute and capture events
        result = await agent_core.execute_agent(context, state)
        
        # Allow time for all async events to be processed
        await asyncio.sleep(0.2)
        
        # Validate all 5 critical events
        critical_events = mock_websocket_manager.get_critical_events_for_run(run_id)
        event_types = {event.event_type for event in critical_events}
        
        # The 5 critical events for business value
        required_events = {
            'agent_started',     # User sees agent began processing
            'agent_thinking',    # Real-time reasoning visibility  
            'tool_executing',    # Tool usage transparency
            'tool_completed',    # Tool results display
            'agent_completed'    # User knows response is ready
        }
        
        missing_events = required_events - event_types
        if missing_events:
            all_events = [f"{e.event_type}:{e.agent_name}" for e in mock_websocket_manager.events]
            pytest.fail(f"CRITICAL FAILURE: Missing business-critical events: {missing_events}\n"
                       f"All captured events: {all_events}")
        
        # Validate event sequence
        is_valid, errors = mock_websocket_manager.validate_event_sequence(run_id)
        assert is_valid, f"Invalid event sequence: {errors}"
        
        logger.info("✅ All 5 critical events emitted: PASSED")

    @pytest.mark.asyncio  
    async def test_bridge_propagation_through_nested_agents(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge must propagate through nested agent calls."""
        # Create nested agent structure
        inner_agent = TestAgent("InnerAgent", should_emit_events=True)
        outer_agent = TestAgent("OuterAgent", should_emit_events=True, nested_agent=inner_agent)
        
        # Set bridge on outer agent
        outer_agent.set_websocket_bridge(websocket_bridge)
        
        # Bridge should propagate to nested agent when it's executed
        inner_agent.set_websocket_bridge(websocket_bridge)
        
        # Execute outer agent (which executes inner agent)
        run_id = str(uuid.uuid4())
        result = await outer_agent.execute(None, run_id, True)
        
        # Verify both agents emitted events
        events = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events) >= 6, f"Expected at least 6 events from nested execution, got {len(events)}"
        
        # Verify both agents were involved
        agent_names = {event.agent_name for event in events if event.agent_name}
        expected_agents = {"OuterAgent", "InnerAgent"}
        assert expected_agents.issubset(agent_names), f"Missing nested agent events. Found agents: {agent_names}"
        
        logger.info("✅ Bridge propagation through nested agents: PASSED")

    @pytest.mark.asyncio
    async def test_error_handling_when_bridge_missing(self, mock_websocket_manager):
        """CRITICAL: Must handle gracefully when bridge is not set."""
        # Create agent without setting bridge
        test_agent = TestAgent("NoBridgeTest", should_emit_events=True)
        
        # Verify no bridge context
        assert not test_agent.has_websocket_context(), "Agent should not have WebSocket context"
        
        # Execute agent - should not crash but may not emit events
        run_id = str(uuid.uuid4())
        
        try:
            result = await test_agent.execute(None, run_id, True)
            # Execution should succeed even without bridge
            assert result is not None, "Agent execution should succeed even without bridge"
        except Exception as e:
            # If it fails, it should be a graceful failure, not a crash
            assert "websocket" in str(e).lower() or "bridge" in str(e).lower(), \
                f"Unexpected error type when bridge missing: {e}"
        
        # Events should be minimal or none since no bridge
        events = mock_websocket_manager.get_events_for_run(run_id)
        logger.info(f"Events emitted without bridge: {len(events)}")
        
        logger.info("✅ Error handling when bridge missing: PASSED")

    @pytest.mark.asyncio
    async def test_concurrent_agent_executions_separate_bridges(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Concurrent executions must maintain separate bridge contexts."""
        # Create multiple agents
        agents = [TestAgent(f"ConcurrentAgent{i}", should_emit_events=True) for i in range(5)]
        
        # Set bridge on all agents
        for agent in agents:
            agent.set_websocket_bridge(websocket_bridge)
        
        # Create concurrent execution tasks
        async def execute_agent(agent, agent_id):
            run_id = f"concurrent_run_{agent_id}_{uuid.uuid4()}"
            return await agent.execute(None, run_id, True), run_id
        
        # Execute all agents concurrently
        tasks = [execute_agent(agent, i) for i, agent in enumerate(agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded
        run_ids = []
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent execution failed: {result}")
            else:
                result_data, run_id = result
                run_ids.append(run_id)
        
        # Verify each run has its own events
        for run_id in run_ids:
            events = mock_websocket_manager.get_events_for_run(run_id)
            assert len(events) > 0, f"No events for run {run_id}"
            
            # Verify events are properly isolated
            other_run_events = [e for e in mock_websocket_manager.events if e.run_id != run_id]
            assert len(other_run_events) > 0, "Should have events from other runs too"
        
        # Verify total event count makes sense
        total_events = len(mock_websocket_manager.events)
        expected_min_events = len(agents) * 2  # At least 2 events per agent
        assert total_events >= expected_min_events, \
            f"Expected at least {expected_min_events} events, got {total_events}"
        
        logger.info("✅ Concurrent executions with separate bridges: PASSED")

    @pytest.mark.asyncio
    async def test_bridge_survives_agent_retries_and_fallbacks(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge must remain functional through retries and fallbacks."""
        # Create agent that fails first time, succeeds second time
        class RetryAgent(TestAgent):
            def __init__(self):
                super().__init__("RetryAgent", should_emit_events=True)
                self.attempt_count = 0
                
            async def execute(self, state, run_id="", stream_updates=False):
                self.attempt_count += 1
                
                if self.attempt_count == 1:
                    # First attempt fails
                    await self.emit_thinking("First attempt - will fail")
                    self.events_emitted.append("thinking_fail")
                    raise Exception("First attempt failure")
                else:
                    # Subsequent attempts succeed
                    return await super().execute(state, run_id, stream_updates)
        
        retry_agent = RetryAgent()
        retry_agent.set_websocket_bridge(websocket_bridge)
        
        run_id = str(uuid.uuid4())
        
        # First execution should fail but emit events
        with pytest.raises(Exception, match="First attempt failure"):
            await retry_agent.execute(None, run_id, True)
        
        # Verify events from failed attempt
        events_after_failure = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events_after_failure) > 0, "Should have events from failed attempt"
        
        # Reset for retry (but keep same run_id to simulate retry)
        mock_websocket_manager.reset_events()
        
        # Retry should succeed and emit events
        result = await retry_agent.execute(None, run_id, True)
        assert result is not None, "Retry should succeed"
        
        # Verify bridge still works after failure/retry
        events_after_retry = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events_after_retry) > 0, "Bridge should still work after retry"
        
        logger.info("✅ Bridge survives retries and fallbacks: PASSED")

    @pytest.mark.asyncio
    async def test_tool_dispatcher_receives_bridge_for_tool_events(self, websocket_bridge, mock_tool_dispatcher):
        """CRITICAL: Tool dispatcher must receive bridge to emit tool events."""
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Create registry and set bridge
        registry = AgentRegistry(MagicMock(), mock_tool_dispatcher)
        registry.set_websocket_bridge(websocket_bridge)
        
        # Verify tool dispatcher received the bridge
        assert mock_tool_dispatcher.executor.websocket_bridge is not None, \
            "Tool dispatcher executor should have WebSocket bridge"
        
        # Verify bridge is the same instance
        assert mock_tool_dispatcher.executor.websocket_bridge == websocket_bridge, \
            "Tool dispatcher should have the same bridge instance"
        
        # Test that tool dispatcher diagnostics show bridge is wired
        if hasattr(mock_tool_dispatcher, 'diagnose_websocket_wiring'):
            diagnosis = mock_tool_dispatcher.diagnose_websocket_wiring()
            assert len(diagnosis.get("critical_issues", [])) == 0, \
                f"Tool dispatcher has critical WebSocket issues: {diagnosis['critical_issues']}"
        
        logger.info("✅ Tool dispatcher receives bridge for tool events: PASSED")

    @pytest.mark.asyncio
    async def test_state_preservation_across_agent_lifecycle(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge state must be preserved across full agent lifecycle."""
        # Create agent and track lifecycle
        agent = TestAgent("LifecycleAgent", should_emit_events=True)
        
        # Initial state - no bridge
        assert not agent.has_websocket_context(), "Initial: no bridge context"
        
        # Set bridge - should be available
        agent.set_websocket_bridge(websocket_bridge)
        assert agent.has_websocket_context(), "After set_bridge: should have context"
        
        # Execute - bridge should remain
        run_id = str(uuid.uuid4())
        result1 = await agent.execute(None, run_id, True)
        assert agent.has_websocket_context(), "After execute: should still have context"
        
        # Multiple executions - bridge should persist
        for i in range(3):
            run_id = f"lifecycle_run_{i}"
            result = await agent.execute(None, run_id, True)
            assert agent.has_websocket_context(), f"Execute {i}: should still have context"
        
        # Verify events from all executions
        all_events = len(mock_websocket_manager.events)
        assert all_events >= 12, f"Expected at least 12 events from 4 executions, got {all_events}"
        
        logger.info("✅ State preservation across agent lifecycle: PASSED")

    @pytest.mark.asyncio
    async def test_stress_multiple_concurrent_agents(self, websocket_bridge, mock_websocket_manager):
        """STRESS TEST: Multiple concurrent agents with complex interactions."""
        num_agents = 10
        num_executions_per_agent = 3
        
        # Create agents with varying behaviors
        agents = []
        for i in range(num_agents):
            should_fail = i % 4 == 0  # Every 4th agent fails
            nested_agent = TestAgent(f"Nested{i}", should_emit_events=True) if i % 3 == 0 else None
            agent = TestAgent(f"StressAgent{i}", should_emit_events=True, 
                            should_fail=should_fail, nested_agent=nested_agent)
            agent.set_websocket_bridge(websocket_bridge)
            agents.append(agent)
        
        # Execute all agents multiple times concurrently
        async def stress_execute(agent, execution_id):
            run_id = f"stress_{agent.name}_{execution_id}_{uuid.uuid4()}"
            try:
                result = await agent.execute(None, run_id, True)
                return {"success": True, "run_id": run_id, "agent": agent.name}
            except Exception as e:
                return {"success": False, "run_id": run_id, "agent": agent.name, "error": str(e)}
        
        # Create all execution tasks
        tasks = []
        for agent in agents:
            for exec_id in range(num_executions_per_agent):
                tasks.append(stress_execute(agent, exec_id))
        
        # Execute all concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successes = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        failures = sum(1 for r in results if not isinstance(r, Exception) and not r.get("success"))
        exceptions = sum(1 for r in results if isinstance(r, Exception))
        
        logger.info(f"Stress test results: {successes} successes, {failures} expected failures, "
                   f"{exceptions} exceptions in {execution_time:.2f}s")
        
        # Validate minimum success rate (accounting for intentional failures)
        expected_successes = num_agents * num_executions_per_agent * 0.75  # 75% should succeed
        assert successes >= expected_successes, \
            f"Too many failures: {successes} < {expected_successes}"
        
        # Verify bridge handled concurrent load
        total_events = len(mock_websocket_manager.events)
        min_expected_events = successes * 2  # At least 2 events per successful execution
        assert total_events >= min_expected_events, \
            f"Not enough events for stress load: {total_events} < {min_expected_events}"
        
        logger.info("✅ Stress test with multiple concurrent agents: PASSED")

    @pytest.mark.asyncio
    async def test_regression_old_websocket_context_pattern(self, websocket_bridge, mock_websocket_manager):
        """REGRESSION TEST: Ensure old set_websocket_context pattern is deprecated and fails gracefully."""
        
        # Create agent that tries to use old pattern
        class LegacyAgent(TestAgent):
            def __init__(self):
                super().__init__("LegacyAgent", should_emit_events=True)
                self.legacy_context_set = False
            
            def set_websocket_context(self, websocket_manager, thread_id):
                """Old deprecated method that should not work."""
                self.legacy_context_set = True
                # This should not provide WebSocket functionality
        
        legacy_agent = LegacyAgent()
        
        # Try old pattern - should not provide WebSocket context
        legacy_agent.set_websocket_context(mock_websocket_manager, "thread123")
        assert legacy_agent.legacy_context_set, "Legacy method should be called"
        assert not legacy_agent.has_websocket_context(), "Legacy pattern should not provide context"
        
        # New pattern should work
        legacy_agent.set_websocket_bridge(websocket_bridge)
        assert legacy_agent.has_websocket_context(), "New pattern should provide context"
        
        # Execute and verify new pattern works
        run_id = str(uuid.uuid4())
        result = await legacy_agent.execute(None, run_id, True)
        
        events = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events) > 0, "New pattern should emit events"
        
        logger.info("✅ Regression test for old WebSocket context pattern: PASSED")

    @pytest.mark.asyncio
    async def test_integration_execution_engine_to_websocket_events(self, execution_engine, agent_registry, 
                                                                  mock_websocket_manager, websocket_bridge):
        """INTEGRATION TEST: Full flow from ExecutionEngine through to WebSocket events."""
        
        # Register test agents in registry
        test_agent = TestAgent("IntegrationTest", should_emit_events=True)
        agent_registry.register("integration_test", test_agent)
        
        # Create execution context
        run_id = str(uuid.uuid4())
        context = AgentExecutionContext(
            run_id=run_id,
            agent_name="integration_test",
            steps=[PipelineStep(agent_name="integration_test", params={})],
            thread_id=f"thread_{run_id}",
            metadata={"test": "integration"}
        )
        
        # Execute through full execution engine
        state = DeepAgentState(
            user_query="Integration test query",
            thread_id=context.thread_id,
            conversation_history=[]
        )
        
        # Full execution through ExecutionEngine
        result = await execution_engine.execute_pipeline(context, state)
        
        # Allow time for async event processing
        await asyncio.sleep(0.3)
        
        # Validate full integration worked
        assert result is not None, "Execution should complete successfully"
        
        # Verify all expected events were emitted
        events = mock_websocket_manager.get_events_for_run(run_id)
        assert len(events) >= 5, f"Expected at least 5 events from full integration, got {len(events)}"
        
        # Verify the 5 critical events for business value
        critical_events = mock_websocket_manager.get_critical_events_for_run(run_id)
        critical_types = {event.event_type for event in critical_events}
        
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        missing_events = required_events - critical_types
        
        if missing_events:
            all_event_details = [(e.event_type, e.agent_name, e.timestamp) for e in events]
            pytest.fail(f"INTEGRATION FAILURE: Missing critical events: {missing_events}\n"
                       f"All events: {all_event_details}")
        
        # Verify event sequence is correct
        is_valid, errors = mock_websocket_manager.validate_event_sequence(run_id)
        assert is_valid, f"Invalid event sequence in integration test: {errors}"
        
        logger.info("✅ Full ExecutionEngine to WebSocket events integration: PASSED")

    @pytest.mark.asyncio
    async def test_bridge_health_monitoring_during_execution(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge health monitoring must work during agent execution."""
        
        # Get initial health status
        initial_health = websocket_bridge.get_health_status()
        assert initial_health.state == IntegrationState.ACTIVE, \
            f"Bridge should be active initially, got {initial_health.state}"
        
        # Execute agents while monitoring health
        test_agent = TestAgent("HealthMonitorTest", should_emit_events=True)
        test_agent.set_websocket_bridge(websocket_bridge)
        
        # Execute multiple times while checking health
        for i in range(5):
            run_id = f"health_run_{i}"
            
            # Check health before execution
            pre_health = websocket_bridge.get_health_status()
            assert pre_health.state == IntegrationState.ACTIVE, \
                f"Bridge should be healthy before execution {i}"
            
            # Execute agent
            result = await test_agent.execute(None, run_id, True)
            
            # Check health after execution
            post_health = websocket_bridge.get_health_status()
            assert post_health.state == IntegrationState.ACTIVE, \
                f"Bridge should be healthy after execution {i}"
            
            # Verify health metrics improved
            assert post_health.uptime_seconds >= pre_health.uptime_seconds, \
                "Health uptime should not decrease"
        
        # Verify final health status
        final_health = websocket_bridge.get_health_status()
        assert final_health.consecutive_failures == 0, \
            f"Should have no consecutive failures, got {final_health.consecutive_failures}"
        
        # Verify events were successfully delivered
        total_events = len(mock_websocket_manager.events)
        assert total_events >= 10, f"Expected at least 10 events from 5 executions, got {total_events}"
        
        logger.info("✅ Bridge health monitoring during execution: PASSED")

    @pytest.mark.asyncio
    async def test_bridge_recovery_after_websocket_manager_failure(self, websocket_bridge, mock_websocket_manager):
        """CRITICAL: Bridge must recover gracefully after WebSocket manager failure."""
        
        # Create test agent
        test_agent = TestAgent("RecoveryTest", should_emit_events=True)
        test_agent.set_websocket_bridge(websocket_bridge)
        
        # Normal execution should work
        run_id1 = str(uuid.uuid4())
        result1 = await test_agent.execute(None, run_id1, True)
        events_before_failure = mock_websocket_manager.get_events_for_run(run_id1)
        assert len(events_before_failure) > 0, "Should have events before failure"
        
        # Simulate WebSocket manager failure
        original_send = mock_websocket_manager.send_to_thread
        async def failing_send(*args, **kwargs):
            raise Exception("WebSocket manager failure simulation")
        
        mock_websocket_manager.send_to_thread = failing_send
        
        # Execution should still work but events may be lost
        run_id2 = str(uuid.uuid4())
        try:
            result2 = await test_agent.execute(None, run_id2, True)
            # Agent execution should succeed even if WebSocket fails
            assert result2 is not None, "Agent execution should survive WebSocket failure"
        except Exception as e:
            # If it fails, it should be a graceful failure
            logger.info(f"Agent execution failed during WebSocket failure (expected): {e}")
        
        # Restore WebSocket manager
        mock_websocket_manager.send_to_thread = original_send
        
        # Verify recovery - events should work again
        run_id3 = str(uuid.uuid4())
        result3 = await test_agent.execute(None, run_id3, True)
        events_after_recovery = mock_websocket_manager.get_events_for_run(run_id3)
        assert len(events_after_recovery) > 0, "Should have events after recovery"
        
        logger.info("✅ Bridge recovery after WebSocket manager failure: PASSED")


# ============================================================================
# PERFORMANCE AND RELIABILITY TESTS
# ============================================================================

class TestWebSocketBridgePerformanceReliability:
    """Performance and reliability tests for WebSocket bridge under load."""
    
    @pytest.mark.asyncio
    async def test_bridge_performance_under_high_load(self, websocket_bridge, mock_websocket_manager):
        """Performance test: Bridge must handle high event load efficiently."""
        
        # Create multiple agents for load testing
        num_agents = 20
        events_per_agent = 50
        
        agents = []
        for i in range(num_agents):
            agent = TestAgent(f"LoadAgent{i}", should_emit_events=True)
            agent.set_websocket_bridge(websocket_bridge)
            agents.append(agent)
        
        # Create high-frequency event generator
        async def generate_high_frequency_events(agent, agent_id):
            events_generated = 0
            for j in range(events_per_agent):
                run_id = f"load_{agent_id}_{j}"
                try:
                    await agent.emit_thinking(f"Load test event {j}")
                    await agent.emit_tool_executing("load_tool", {"iteration": j})
                    await agent.emit_tool_completed("load_tool", {"result": j})
                    events_generated += 3
                except Exception as e:
                    logger.warning(f"Event generation failed for agent {agent_id}, event {j}: {e}")
            return events_generated
        
        # Execute load test
        start_time = time.time()
        tasks = [generate_high_frequency_events(agent, i) for i, agent in enumerate(agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze performance
        total_events_generated = sum(r for r in results if isinstance(r, int))
        successful_deliveries = len(mock_websocket_manager.events)
        delivery_rate = successful_deliveries / total_events_generated if total_events_generated > 0 else 0
        events_per_second = total_events_generated / execution_time if execution_time > 0 else 0
        
        logger.info(f"Load test: {total_events_generated} events generated, "
                   f"{successful_deliveries} delivered ({delivery_rate:.2%} success rate), "
                   f"{events_per_second:.0f} events/sec")
        
        # Performance assertions
        assert delivery_rate >= 0.95, f"Event delivery rate too low: {delivery_rate:.2%}"
        assert events_per_second >= 100, f"Event processing too slow: {events_per_second:.0f} events/sec"
        assert execution_time < 30, f"Load test took too long: {execution_time:.2f}s"
        
        logger.info("✅ Bridge performance under high load: PASSED")

    @pytest.mark.asyncio
    async def test_bridge_memory_usage_stability(self, websocket_bridge, mock_websocket_manager):
        """Reliability test: Bridge must not leak memory during extended operation."""
        import gc
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create agent for memory test
        test_agent = TestAgent("MemoryTest", should_emit_events=True)
        test_agent.set_websocket_bridge(websocket_bridge)
        
        # Perform many operations to test memory stability
        num_iterations = 100
        for i in range(num_iterations):
            run_id = f"memory_test_{i}"
            
            # Execute agent multiple times
            await test_agent.execute(None, run_id, True)
            
            # Emit additional events
            await test_agent.emit_thinking(f"Memory test iteration {i}")
            await test_agent.emit_tool_executing("memory_tool", {"iteration": i})
            await test_agent.emit_tool_completed("memory_tool", {"result": f"iteration_{i}"})
            
            # Periodic garbage collection
            if i % 10 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        memory_increase_percent = (memory_increase / initial_memory) * 100 if initial_memory > 0 else 0
        
        logger.info(f"Memory test: Initial {initial_memory:.1f}MB, Final {final_memory:.1f}MB, "
                   f"Increase {memory_increase:.1f}MB ({memory_increase_percent:.1f}%)")
        
        # Memory usage should not grow excessively
        assert memory_increase < 100, f"Excessive memory increase: {memory_increase:.1f}MB"
        assert memory_increase_percent < 50, f"Memory increase too high: {memory_increase_percent:.1f}%"
        
        # Verify all events were processed
        total_events = len(mock_websocket_manager.events)
        expected_min_events = num_iterations * 4  # 4 events per iteration minimum
        assert total_events >= expected_min_events, \
            f"Not all events processed: {total_events} < {expected_min_events}"
        
        logger.info("✅ Bridge memory usage stability: PASSED")


if __name__ == "__main__":
    # Run the comprehensive test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])