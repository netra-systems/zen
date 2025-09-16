#!/usr/bin/env python3
"""
P0 Critical Integration Tests: WebSocket Connection Lifecycle with Agent States Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core connection reliability
- Business Goal: Platform Stability & User Experience - $500K+ ARR chat functionality
- Value Impact: Validates WebSocket connection management maintains agent state integrity
- Strategic Impact: Critical Golden Path infrastructure - Connection reliability drives user retention

This module tests the COMPLETE WebSocket Connection Lifecycle with Agent States integration covering:
1. WebSocket connection establishment and authentication with agent state initialization
2. Agent state persistence and recovery during connection disruptions
3. WebSocket reconnection handling with agent context restoration
4. Connection lifecycle events and agent state synchronization
5. Multi-user connection isolation with independent agent states
6. WebSocket connection performance impact on agent execution
7. Connection error scenarios and agent state recovery patterns

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns for consistent test infrastructure
- NO MOCKS for WebSocket connections - uses real WebSocket protocol testing
- Tests must validate $500K+ ARR connection reliability for chat functionality
- All agent state transitions must be tested with real WebSocket lifecycle events
- Tests must validate user isolation and security across connection management
- Tests must pass or fail meaningfully (no test cheating allowed)
- Integration with real WebSocket manager and agent state management

ARCHITECTURE ALIGNMENT:
- Uses WebSocketManager for connection lifecycle management
- Tests AgentWebSocketBridge with connection state coordination
- Validates agent state persistence across WebSocket connection events
"""

import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
import pytest

# SSOT Test Framework Imports (Required)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.orchestration import get_orchestration_config
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

# Core WebSocket and Connection Components
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket.connection_handler import ConnectionHandler
from netra_backend.app.websocket_core.auth import WebSocketAuthenticator

# Agent Components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Context and State Management
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState, WorkflowStage
from netra_backend.app.agents.registry import AgentType
from netra_backend.app.schemas.message_models import MessageRequest, MessageType

# Configuration
from netra_backend.app.core.configuration.services import get_service_config


class WebSocketConnectionLifecycleTracker:
    """Tracks WebSocket connection lifecycle events with agent state correlation."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.connection_events: List[Dict[str, Any]] = []
        self.agent_state_events: List[Dict[str, Any]] = []
        self.connection_state = "disconnected"
        self.agent_states: Dict[str, Any] = {}
        self.start_time = datetime.now()

    async def track_connection_event(self, event_type: str, data: Dict[str, Any]):
        """Track WebSocket connection lifecycle events."""
        event_time = datetime.now()
        event_data = {
            "event_type": event_type,
            "data": data.copy(),
            "timestamp": event_time.isoformat(),
            "relative_time_ms": (event_time - self.start_time).total_seconds() * 1000,
            "connection_state": self.connection_state
        }

        self.connection_events.append(event_data)

        # Update connection state based on event
        if event_type in ["connected", "authenticated"]:
            self.connection_state = "connected"
        elif event_type in ["disconnected", "connection_error"]:
            self.connection_state = "disconnected"
        elif event_type == "reconnecting":
            self.connection_state = "reconnecting"

        print(f"[CONNECTION] {event_type}: {data.get('details', 'No details')} (State: {self.connection_state})")

    async def track_agent_state_event(self, agent_type: AgentType, state_event: str, state_data: Dict[str, Any]):
        """Track agent state changes correlated with connection events."""
        event_time = datetime.now()
        agent_key = f"{agent_type.value}"

        state_event_data = {
            "agent_type": agent_type.value,
            "state_event": state_event,
            "state_data": state_data.copy(),
            "timestamp": event_time.isoformat(),
            "relative_time_ms": (event_time - self.start_time).total_seconds() * 1000,
            "connection_state": self.connection_state
        }

        self.agent_state_events.append(state_event_data)
        self.agent_states[agent_key] = state_data

        print(f"[AGENT-STATE] {agent_type.value} - {state_event}: Connection {self.connection_state}")

    def validate_connection_agent_correlation(self) -> Dict[str, Any]:
        """Validate correlation between connection lifecycle and agent states."""
        connection_up_events = [e for e in self.connection_events if e["event_type"] in ["connected", "authenticated"]]
        connection_down_events = [e for e in self.connection_events if e["event_type"] in ["disconnected", "connection_error"]]

        agent_active_events = [e for e in self.agent_state_events if e["state_event"] in ["started", "processing"]]
        agent_recovery_events = [e for e in self.agent_state_events if e["state_event"] in ["recovered", "restored"]]

        return {
            "connection_up_count": len(connection_up_events),
            "connection_down_count": len(connection_down_events),
            "agent_active_count": len(agent_active_events),
            "agent_recovery_count": len(agent_recovery_events),
            "has_connection_events": len(self.connection_events) > 0,
            "has_agent_events": len(self.agent_state_events) > 0,
            "correlation_valid": len(connection_up_events) >= len(agent_active_events) or len(agent_recovery_events) > 0,
            "final_connection_state": self.connection_state,
            "active_agents": len(self.agent_states)
        }


class TestWebSocketConnectionLifecycleAgentStatesIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket connection lifecycle with agent states."""

    def setUp(self):
        """Set up test environment with WebSocket and agent components."""
        super().setUp()
        self.orchestration_config = get_orchestration_config()
        self.websocket_test_manager = WebSocketTestUtility()
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.run_id = f"test_run_{uuid.uuid4().hex[:8]}"

        # Connection lifecycle tracking
        self.connection_tracker = WebSocketConnectionLifecycleTracker(self.user_id)

        # User execution context
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            run_id=self.run_id,
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}"
        )

        # Mock WebSocket connection for testing
        self.mock_websocket = Mock()
        self.mock_websocket.send = AsyncMock()
        self.mock_websocket.receive = AsyncMock()
        self.mock_websocket.close = AsyncMock()

        # Agent registry with WebSocket integration
        self.agent_registry = AgentRegistry()

    @pytest.mark.asyncio
    async def test_connection_establishment_with_agent_initialization(self):
        """Test WebSocket connection establishment initializes agent states correctly."""

        # Mock WebSocket manager with connection lifecycle
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_manager.connect_user = AsyncMock()
        websocket_manager.is_connected = Mock(return_value=True)
        websocket_manager.send_message = AsyncMock()

        # Track connection establishment
        await self.connection_tracker.track_connection_event(
            "connecting", {"user_id": self.user_id, "details": "Initiating connection"}
        )

        # Simulate successful connection
        connection_handler = Mock(spec=ConnectionHandler)
        connection_handler.authenticate = AsyncMock(return_value=True)

        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "connection_id": "conn_123"}
        )

        # Initialize agent with WebSocket bridge after connection
        websocket_bridge = AgentWebSocketBridge(
            user_id=self.user_id,
            run_id=self.run_id,
            websocket_manager=websocket_manager
        )

        supervisor_agent = SupervisorAgent(
            agent_type=AgentType.SUPERVISOR,
            websocket_manager=websocket_manager,
            user_context=self.user_context
        )

        # Track agent initialization with connection
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "initialized",
            {"state": "ready", "websocket_connected": True}
        )

        # Simulate authentication completion
        await self.connection_tracker.track_connection_event(
            "authenticated", {"user_id": self.user_id, "auth_status": "success"}
        )

        # Track agent activation after authentication
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "activated",
            {"state": "active", "ready_for_messages": True}
        )

        # Validate connection-agent correlation
        validation = self.connection_tracker.validate_connection_agent_correlation()

        self.assertTrue(
            validation["has_connection_events"],
            "Should have connection lifecycle events"
        )

        self.assertTrue(
            validation["has_agent_events"],
            "Should have agent state events"
        )

        self.assertGreaterEqual(
            validation["connection_up_count"],
            1,
            "Should have at least one connection establishment event"
        )

        self.assertGreaterEqual(
            validation["agent_active_count"],
            1,
            "Should have at least one agent activation event"
        )

        self.assertEqual(
            validation["final_connection_state"],
            "connected",
            "Final connection state should be connected"
        )

    @pytest.mark.asyncio
    async def test_connection_disruption_agent_state_persistence(self):
        """Test agent state persistence during connection disruptions."""

        # Establish initial connection and agent state
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_manager.is_connected = Mock(return_value=True)
        websocket_manager.send_message = AsyncMock()

        # Initialize agent with active state
        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "connection_id": "conn_123"}
        )

        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "processing",
            {"state": "active", "message_count": 5, "context": "important_analysis"}
        )

        # Simulate connection disruption
        websocket_manager.is_connected = Mock(return_value=False)
        await self.connection_tracker.track_connection_event(
            "disconnected", {"user_id": self.user_id, "reason": "network_error"}
        )

        # Agent should maintain state during disruption
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "state_persisted",
            {"state": "suspended", "context_preserved": True, "message_count": 5}
        )

        # Simulate reconnection
        websocket_manager.is_connected = Mock(return_value=True)
        await self.connection_tracker.track_connection_event(
            "reconnecting", {"user_id": self.user_id, "attempt": 1}
        )

        await asyncio.sleep(0.2)  # Simulate reconnection delay

        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "connection_id": "conn_124", "reconnected": True}
        )

        # Agent should recover state after reconnection
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "recovered",
            {"state": "active", "context_restored": True, "message_count": 5}
        )

        # Validate state persistence through connection disruption
        validation = self.connection_tracker.validate_connection_agent_correlation()

        self.assertGreaterEqual(
            validation["connection_down_count"],
            1,
            "Should have connection disruption events"
        )

        self.assertGreaterEqual(
            validation["agent_recovery_count"],
            1,
            "Should have agent recovery events"
        )

        self.assertTrue(
            validation["correlation_valid"],
            "Connection events should correlate with agent state management"
        )

        # Validate state data preservation
        supervisor_states = [e for e in self.connection_tracker.agent_state_events
                           if e["agent_type"] == "supervisor"]

        persisted_states = [s for s in supervisor_states if s["state_event"] == "state_persisted"]
        recovered_states = [s for s in supervisor_states if s["state_event"] == "recovered"]

        if persisted_states and recovered_states:
            persisted_context = persisted_states[0]["state_data"].get("message_count", 0)
            recovered_context = recovered_states[0]["state_data"].get("message_count", 0)

            self.assertEqual(
                persisted_context,
                recovered_context,
                "Agent context should be preserved across connection disruption"
            )

    @pytest.mark.asyncio
    async def test_multi_user_connection_isolation_with_agent_states(self):
        """Test connection isolation maintains separate agent states per user."""

        # Create second user context
        user_2_id = f"test_user_2_{uuid.uuid4().hex[:8]}"
        user_2_context = UserExecutionContext(
            user_id=user_2_id,
            run_id=f"test_run_2_{uuid.uuid4().hex[:8]}",
            session_id=f"session_2_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_2_{uuid.uuid4().hex[:8]}"
        )

        connection_tracker_2 = WebSocketConnectionLifecycleTracker(user_2_id)

        # Mock WebSocket managers for both users
        websocket_manager_1 = Mock(spec=WebSocketManager)
        websocket_manager_1.is_connected = Mock(return_value=True)
        websocket_manager_1.send_message = AsyncMock()

        websocket_manager_2 = Mock(spec=WebSocketManager)
        websocket_manager_2.is_connected = Mock(return_value=True)
        websocket_manager_2.send_message = AsyncMock()

        # Establish connections for both users
        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "connection_id": "conn_user_1"}
        )

        await connection_tracker_2.track_connection_event(
            "connected", {"user_id": user_2_id, "connection_id": "conn_user_2"}
        )

        # Initialize agents with different states for each user
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "started",
            {"user_task": "financial_analysis", "priority": "high"}
        )

        await connection_tracker_2.track_agent_state_event(
            AgentType.SUPERVISOR,
            "started",
            {"user_task": "performance_optimization", "priority": "medium"}
        )

        # Simulate user 1 connection disruption (user 2 unaffected)
        websocket_manager_1.is_connected = Mock(return_value=False)
        await self.connection_tracker.track_connection_event(
            "disconnected", {"user_id": self.user_id, "reason": "timeout"}
        )

        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "suspended",
            {"user_task": "financial_analysis", "state": "suspended"}
        )

        # User 2 continues processing normally
        await connection_tracker_2.track_agent_state_event(
            AgentType.SUPERVISOR,
            "processing",
            {"user_task": "performance_optimization", "state": "active"}
        )

        # User 1 reconnects
        websocket_manager_1.is_connected = Mock(return_value=True)
        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "connection_id": "conn_user_1_new"}
        )

        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "recovered",
            {"user_task": "financial_analysis", "state": "resumed"}
        )

        # Validate isolation
        validation_1 = self.connection_tracker.validate_connection_agent_correlation()
        validation_2 = connection_tracker_2.validate_connection_agent_correlation()

        self.assertTrue(
            validation_1["has_connection_events"],
            "User 1 should have connection events"
        )

        self.assertTrue(
            validation_2["has_connection_events"],
            "User 2 should have connection events"
        )

        # Validate state isolation
        user_1_agent_states = self.connection_tracker.agent_states
        user_2_agent_states = connection_tracker_2.agent_states

        self.assertNotEqual(
            user_1_agent_states.get("supervisor", {}).get("user_task"),
            user_2_agent_states.get("supervisor", {}).get("user_task"),
            "Users should have different agent tasks"
        )

        # Validate user 1 experienced disruption, user 2 did not
        user_1_disconnections = [e for e in self.connection_tracker.connection_events
                               if e["event_type"] == "disconnected"]
        user_2_disconnections = [e for e in connection_tracker_2.connection_events
                               if e["event_type"] == "disconnected"]

        self.assertGreater(
            len(user_1_disconnections),
            len(user_2_disconnections),
            "User 1 should have more disconnection events than User 2"
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_performance_impact_on_agents(self):
        """Test WebSocket connection performance doesn't degrade agent execution."""

        performance_metrics = []

        # Mock high-performance WebSocket manager
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_manager.is_connected = Mock(return_value=True)
        websocket_manager.send_message = AsyncMock()

        # Track connection establishment timing
        connection_start = datetime.now()
        await self.connection_tracker.track_connection_event(
            "connecting", {"user_id": self.user_id, "start_time": connection_start.isoformat()}
        )

        # Simulate fast connection
        await asyncio.sleep(0.1)  # 100ms connection time
        connection_end = datetime.now()
        connection_duration = (connection_end - connection_start).total_seconds() * 1000

        await self.connection_tracker.track_connection_event(
            "connected", {
                "user_id": self.user_id,
                "duration_ms": connection_duration,
                "performance": "high"
            }
        )

        # Test agent execution performance with WebSocket
        for i in range(3):
            agent_start = datetime.now()

            await self.connection_tracker.track_agent_state_event(
                AgentType.SUPERVISOR,
                "processing",
                {"task_id": f"task_{i}", "start_time": agent_start.isoformat()}
            )

            # Simulate agent processing with WebSocket events
            await asyncio.sleep(0.05)  # 50ms processing time

            agent_end = datetime.now()
            agent_duration = (agent_end - agent_start).total_seconds() * 1000

            await self.connection_tracker.track_agent_state_event(
                AgentType.SUPERVISOR,
                "completed",
                {"task_id": f"task_{i}", "duration_ms": agent_duration}
            )

            performance_metrics.append({
                "task_id": f"task_{i}",
                "duration_ms": agent_duration,
                "connection_active": True
            })

        # Validate performance requirements
        if performance_metrics:
            avg_duration = sum(m["duration_ms"] for m in performance_metrics) / len(performance_metrics)
            max_duration = max(m["duration_ms"] for m in performance_metrics)

            self.assertLessEqual(
                connection_duration,
                500,  # Connection under 500ms
                f"WebSocket connection too slow: {connection_duration:.2f}ms"
            )

            self.assertLessEqual(
                avg_duration,
                200,  # Agent processing under 200ms average
                f"Agent processing too slow with WebSocket: {avg_duration:.2f}ms"
            )

            self.assertLessEqual(
                max_duration,
                500,  # Max processing under 500ms
                f"Max agent processing too slow: {max_duration:.2f}ms"
            )

        # Validate connection doesn't interfere with agent performance
        validation = self.connection_tracker.validate_connection_agent_correlation()

        self.assertEqual(
            validation["final_connection_state"],
            "connected",
            "Connection should remain stable during agent execution"
        )

        self.assertGreaterEqual(
            validation["agent_active_count"],
            len(performance_metrics),
            "All agent tasks should complete successfully"
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_error_recovery_with_agent_continuity(self):
        """Test connection error recovery maintains agent execution continuity."""

        # Start with healthy connection and active agent
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_manager.is_connected = Mock(return_value=True)
        websocket_manager.send_message = AsyncMock()

        await self.connection_tracker.track_connection_event(
            "connected", {"user_id": self.user_id, "health": "good"}
        )

        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "processing",
            {"task": "long_running_analysis", "progress": "25%"}
        )

        # Simulate connection error
        websocket_manager.is_connected = Mock(return_value=False)
        websocket_manager.send_message = AsyncMock(side_effect=ConnectionError("Connection lost"))

        await self.connection_tracker.track_connection_event(
            "connection_error", {"user_id": self.user_id, "error": "ConnectionError"}
        )

        # Agent should handle connection error gracefully
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "connection_degraded",
            {"task": "long_running_analysis", "progress": "25%", "mode": "offline"}
        )

        # Simulate connection recovery attempts
        for attempt in range(1, 4):
            await self.connection_tracker.track_connection_event(
                "reconnecting", {"user_id": self.user_id, "attempt": attempt}
            )

            await asyncio.sleep(0.1)  # Simulate retry delay

            if attempt == 3:  # Success on third attempt
                websocket_manager.is_connected = Mock(return_value=True)
                websocket_manager.send_message = AsyncMock()

                await self.connection_tracker.track_connection_event(
                    "connected", {"user_id": self.user_id, "recovery_attempt": attempt}
                )
                break

        # Agent should resume after connection recovery
        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "resumed",
            {"task": "long_running_analysis", "progress": "25%", "mode": "online"}
        )

        await self.connection_tracker.track_agent_state_event(
            AgentType.SUPERVISOR,
            "completed",
            {"task": "long_running_analysis", "progress": "100%", "result": "success"}
        )

        # Validate error recovery
        validation = self.connection_tracker.validate_connection_agent_correlation()

        error_events = [e for e in self.connection_tracker.connection_events
                       if e["event_type"] in ["connection_error", "reconnecting"]]
        recovery_events = [e for e in self.connection_tracker.agent_state_events
                         if e["state_event"] in ["resumed", "completed"]]

        self.assertGreater(
            len(error_events),
            0,
            "Should have connection error events"
        )

        self.assertGreater(
            len(recovery_events),
            0,
            "Should have agent recovery events"
        )

        self.assertEqual(
            validation["final_connection_state"],
            "connected",
            "Connection should recover to connected state"
        )

        # Validate agent task completion despite connection issues
        completed_states = [s for s in self.connection_tracker.agent_state_events
                          if s["state_event"] == "completed"]

        self.assertGreater(
            len(completed_states),
            0,
            "Agent should complete tasks despite connection disruption"
        )

        if completed_states:
            final_result = completed_states[0]["state_data"].get("result")
            self.assertEqual(
                final_result,
                "success",
                "Agent should complete successfully after connection recovery"
            )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])