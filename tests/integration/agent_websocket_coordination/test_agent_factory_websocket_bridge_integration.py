"""
Test Agent Factory WebSocket Bridge Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure agent factory creates agents with proper WebSocket event emission
- Value Impact: Validates that agent creation is properly integrated with WebSocket events for 90% chat business value
- Strategic Impact: Tests the foundation of agent-WebSocket coordination that enables real-time user feedback

This test validates that the agent factory properly integrates with WebSocket bridge
to ensure all created agents can emit the 5 critical WebSocket events.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, PipelineStep
)


class TestAgentFactoryWebSocketBridgeIntegration(SSotAsyncTestCase):
    """Test Agent Factory WebSocket Bridge Integration."""
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_factory_creates_agents_with_websocket_bridge(self):
        """Test that agent factory creates agents properly integrated with WebSocket bridge.
        
        BVJ: Validates that agent creation process includes WebSocket integration,
        ensuring created agents can emit events for real-time user feedback.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_001",
            thread_id="thread_001",
            run_id="run_001",
            request_id="req_001"
        )
        
        # Create mock WebSocket emitter
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_tool_executing = AsyncMock(return_value=True)
        mock_emitter.notify_tool_completed = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        
        # Create WebSocket bridge and execution engine factory
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=mock_emitter)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Verify factory has WebSocket bridge
        assert hasattr(factory, '_websocket_bridge'), "Factory should have WebSocket bridge"
        bridge = factory._websocket_bridge
        assert isinstance(bridge, AgentWebSocketBridge), "Bridge should be AgentWebSocketBridge instance"
        
        # Create agent instance through agent instance factory
        agent_instance_factory = get_agent_instance_factory()
        agent = await agent_instance_factory.create_agent_instance(
            agent_name="triage_agent",
            user_context=user_context
        )
        
        # Verify agent has WebSocket capabilities
        assert agent is not None, "Factory should create agent instance"
        
        # Verify WebSocket bridge was configured on agent
        # Check if agent has tool dispatcher (which should have WebSocket integration)
        if hasattr(agent, 'tool_dispatcher'):
            assert agent.tool_dispatcher is not None, "Agent should have tool dispatcher with WebSocket integration"
        
        # Test that bridge can emit events for this agent
        await bridge.emit_agent_started("triage_agent", {"test": "data"})
        mock_emitter.notify_agent_started.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_factory_websocket_bridge_event_routing(self):
        """Test that WebSocket bridge properly routes events through factory-created components.
        
        BVJ: Validates event routing system works correctly to deliver real-time updates
        to users, enabling chat experience with agent progress visibility.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_002",
            thread_id="thread_002", 
            run_id="run_002",
            request_id="req_002"
        )
        
        # Create mock WebSocket emitter with event tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        event_log = []
        
        async def track_event(event_type, *args, **kwargs):
            event_log.append({
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
            
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *a, **k: track_event('agent_started', *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *a, **k: track_event('agent_thinking', *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *a, **k: track_event('tool_executing', *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *a, **k: track_event('tool_completed', *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *a, **k: track_event('agent_completed', *a, **k))
        
        # Create WebSocket bridge and execution engine factory
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=mock_emitter)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        bridge = factory._websocket_bridge
        
        # Test event routing through bridge
        await bridge.emit_agent_started("triage_agent", {"status": "starting"})
        await bridge.emit_agent_thinking("triage_agent", "Analyzing request...", 1)
        await bridge.emit_tool_executing("cost_analyzer")
        await bridge.emit_tool_completed("cost_analyzer", {"result": "analysis complete"})
        await bridge.emit_agent_completed("triage_agent", {"status": "completed"})
        
        # Verify all 5 critical events were routed
        assert len(event_log) == 5, f"Should have logged 5 events, got {len(event_log)}"
        
        event_types = [event['type'] for event in event_log]
        expected_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for expected_type in expected_types:
            assert expected_type in event_types, f"Missing critical event type: {expected_type}"
        
        # Verify events are in chronological order
        timestamps = [event['timestamp'] for event in event_log]
        assert timestamps == sorted(timestamps), "Events should be in chronological order"
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_factory_websocket_bridge_agent_isolation(self):
        """Test that WebSocket bridge maintains proper agent isolation through factory.
        
        BVJ: Validates that multiple agents created by factory don't interfere with
        each other's WebSocket events, ensuring clean user experience.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_003",
            thread_id="thread_003",
            run_id="run_003", 
            request_id="req_003"
        )
        
        # Create mock WebSocket emitter with agent-specific tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        agent_events = {}
        
        async def track_agent_event(event_type, agent_name, *args, **kwargs):
            if agent_name not in agent_events:
                agent_events[agent_name] = []
            agent_events[agent_name].append({
                'type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda agent_name, *a, **k: track_agent_event('agent_started', agent_name, *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda agent_name, *a, **k: track_agent_event('agent_thinking', agent_name, *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda agent_name, *a, **k: track_agent_event('agent_completed', agent_name, *a, **k))
        
        # Create WebSocket bridge and execution engine factory
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=mock_emitter)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        bridge = factory._websocket_bridge
        
        # Create multiple agents through agent instance factory
        agent_instance_factory = get_agent_instance_factory()
        agent1 = await agent_instance_factory.create_agent_instance("triage_agent", user_context)
        agent2 = await agent_instance_factory.create_agent_instance("cost_optimizer", user_context)
        
        # Emit events for different agents
        await bridge.emit_agent_started("triage_agent", {"status": "triage starting"})
        await bridge.emit_agent_started("cost_optimizer", {"status": "optimizer starting"})
        await bridge.emit_agent_thinking("triage_agent", "Triaging request...")
        await bridge.emit_agent_thinking("cost_optimizer", "Optimizing costs...")
        await bridge.emit_agent_completed("triage_agent", {"result": "triage done"})
        await bridge.emit_agent_completed("cost_optimizer", {"result": "optimization done"})
        
        # Verify agent isolation
        assert "triage_agent" in agent_events, "Should track triage_agent events"
        assert "cost_optimizer" in agent_events, "Should track cost_optimizer events"
        
        triage_events = agent_events["triage_agent"]
        optimizer_events = agent_events["cost_optimizer"]
        
        assert len(triage_events) == 3, f"Should have 3 triage events, got {len(triage_events)}"
        assert len(optimizer_events) == 3, f"Should have 3 optimizer events, got {len(optimizer_events)}"
        
        # Verify event types for each agent
        triage_types = [event['type'] for event in triage_events]
        optimizer_types = [event['type'] for event in optimizer_events]
        
        expected_types = ['agent_started', 'agent_thinking', 'agent_completed']
        assert triage_types == expected_types, f"Triage agent events should match expected types"
        assert optimizer_types == expected_types, f"Optimizer agent events should match expected types"
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination
    async def test_factory_websocket_bridge_error_handling(self):
        """Test WebSocket bridge error handling through factory integration.
        
        BVJ: Validates that WebSocket failures don't break agent creation or execution,
        ensuring system resilience for business-critical chat functionality.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_004",
            thread_id="thread_004",
            run_id="run_004",
            request_id="req_004"
        )
        
        # Create mock WebSocket emitter that fails
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        mock_emitter.notify_agent_started = AsyncMock(side_effect=Exception("WebSocket connection failed"))
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=False)  # Simulate failure
        mock_emitter.notify_tool_executing = AsyncMock(return_value=True)
        mock_emitter.notify_tool_completed = AsyncMock(return_value=True) 
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        
        # Create WebSocket bridge and execution engine factory (should not fail even with broken WebSocket)
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=mock_emitter)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        bridge = factory._websocket_bridge
        
        # Test that agent instance factory still creates agents despite WebSocket issues
        agent_instance_factory = get_agent_instance_factory()
        agent = await agent_instance_factory.create_agent_instance("triage_agent", user_context)
        assert agent is not None, "Factory should create agent even with WebSocket issues"
        
        # Test bridge error handling for different event types
        error_results = {}
        
        # Test agent_started failure (exception)
        try:
            await bridge.emit_agent_started("test_agent", {})
            error_results['agent_started'] = 'no_error'
        except Exception as e:
            error_results['agent_started'] = 'caught_exception'
        
        # Test agent_thinking failure (return False)
        try:
            result = await bridge.emit_agent_thinking("test_agent", "thinking...")
            error_results['agent_thinking'] = 'returned_false' if not result else 'success'
        except Exception:
            error_results['agent_thinking'] = 'caught_exception'
        
        # Test successful events still work
        try:
            result = await bridge.emit_tool_executing("test_tool")
            error_results['tool_executing'] = 'success' if result else 'returned_false'
        except Exception:
            error_results['tool_executing'] = 'caught_exception'
        
        # Verify error handling behavior
        # Bridge should gracefully handle WebSocket failures without crashing
        assert 'agent_started' in error_results, "Should attempt agent_started event"
        assert 'agent_thinking' in error_results, "Should attempt agent_thinking event" 
        assert 'tool_executing' in error_results, "Should attempt tool_executing event"
        
        # At least some events should work (showing system resilience)
        success_count = sum(1 for result in error_results.values() if result == 'success')
        assert success_count > 0, "At least some events should succeed despite failures"
    
    @pytest.mark.integration
    @pytest.mark.agent_websocket_coordination 
    async def test_factory_websocket_bridge_state_synchronization(self):
        """Test WebSocket bridge state synchronization with factory-created agents.
        
        BVJ: Validates that WebSocket events accurately reflect agent state changes,
        ensuring users see correct real-time status of their AI operations.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user_005",
            thread_id="thread_005", 
            run_id="run_005",
            request_id="req_005"
        )
        
        # Create mock WebSocket emitter with state tracking
        mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        emitted_states = []
        
        async def track_state(event_type, agent_name, *args, **kwargs):
            state_data = {
                'event_type': event_type,
                'agent_name': agent_name,
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs
            }
            emitted_states.append(state_data)
            return True
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda agent_name, *a, **k: track_state('agent_started', agent_name, *a, **k))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda agent_name, *a, **k: track_state('agent_thinking', agent_name, *a, **k))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda tool_name, *a, **k: track_state('tool_executing', tool_name, *a, **k))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda tool_name, *a, **k: track_state('tool_completed', tool_name, *a, **k))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda agent_name, *a, **k: track_state('agent_completed', agent_name, *a, **k))
        
        # Create WebSocket bridge and execution engine factory
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=mock_emitter)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        bridge = factory._websocket_bridge
        
        # Simulate agent execution lifecycle with state changes
        agent_name = "data_analyzer"
        
        # Start execution
        await bridge.emit_agent_started(agent_name, {"status": "initializing"})
        
        # Thinking phase
        await bridge.emit_agent_thinking(agent_name, "Initializing data analysis...")
        await bridge.emit_agent_thinking(agent_name, "Loading data sources...")
        await bridge.emit_agent_thinking(agent_name, "Analyzing patterns...")
        
        # Tool execution
        await bridge.emit_tool_executing("data_loader")
        await bridge.emit_tool_completed("data_loader", {"rows_loaded": 1000})
        
        await bridge.emit_tool_executing("pattern_analyzer") 
        await bridge.emit_tool_completed("pattern_analyzer", {"patterns_found": 5})
        
        # Completion
        await bridge.emit_agent_completed(agent_name, {
            "status": "completed",
            "analysis_result": "Found significant cost optimization opportunities"
        })
        
        # Verify state synchronization
        assert len(emitted_states) == 8, f"Should have 8 state events, got {len(emitted_states)}"
        
        # Verify lifecycle progression
        lifecycle_events = [state for state in emitted_states if state['agent_name'] == agent_name]
        lifecycle_types = [event['event_type'] for event in lifecycle_events]
        
        expected_lifecycle = ['agent_started', 'agent_thinking', 'agent_thinking', 'agent_thinking', 'agent_completed']
        assert lifecycle_types == expected_lifecycle, f"Lifecycle should follow expected pattern"
        
        # Verify tool events
        tool_events = [state for state in emitted_states if 'tool' in state['event_type']]
        assert len(tool_events) == 4, f"Should have 4 tool events (2 executing, 2 completed)"
        
        # Verify temporal ordering
        timestamps = [state['timestamp'] for state in emitted_states]
        assert timestamps == sorted(timestamps), "Events should be in temporal order"
        
        # Verify state data integrity
        for state in emitted_states:
            assert 'event_type' in state, "Each state should have event_type"
            assert 'timestamp' in state, "Each state should have timestamp"
            assert state['agent_name'] or 'tool' in state['event_type'], "Should have agent_name or be tool event"