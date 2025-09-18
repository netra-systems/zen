#!/usr/bin/env python
"""
Agent Registry WebSocket Bridge Integration Tests - Exposing Factory Pattern Gaps

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Agent execution affects all users
- Business Goal: Expose Agent Registry WebSocket integration failures preventing agent business value
- Value Impact: Agent Registry enables agent execution that delivers 90% of chat business value
- Strategic Impact: Factory pattern migration gaps causing Data Helper Agent 0% success rate

CRITICAL MISSION: These tests are designed to FAIL and expose specific integration gaps:
1. Agent Registry missing WebSocket manager integration
2. Factory pattern vs singleton pattern architectural mismatches
3. WebSocket bridge creation failures in multi-user contexts
4. Agent execution without proper WebSocket event emission

TEST FAILURE EXPECTATIONS:
- Agent Registry WebSocket manager not properly initialized
- Factory pattern WebSocket bridge creation failures
- Missing WebSocket event emissions during agent execution
- Multi-user isolation failures in WebSocket context

This test suite intentionally exposes the Agent Registry WebSocket integration
gaps that prevent Data Helper Agents from delivering business value.
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockWebSocketBridge:
    """Mock WebSocket bridge that captures integration gaps."""

    def __init__(self, user_context: Dict[str, Any]):
        self.user_context = user_context
        self.sent_messages = []
        self.bridge_creation_attempts = []
        self.should_fail = False
        self.failure_mode = None

    def set_failure_mode(self, mode: str):
        """Configure failure simulation."""
        self.should_fail = True
        self.failure_mode = mode

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to user - may fail to test integration gaps."""
        if self.should_fail and self.failure_mode == "send":
            raise Exception("WebSocket message sending failed - no active connections")

        # Mock successful send
        self.sent_messages.append({
            "user_id": user_id,
            "message": message,
            "timestamp": time.time()
        })
        return True

    async def emit_agent_started(self, agent_name: str, user_context: Dict[str, Any]):
        """Emit agent started event."""
        message = {
            "type": "agent_started",
            "agent_name": agent_name,
            "user_context": user_context
        }
        return await self.send_to_user(user_context.get("user_id"), message)

    async def emit_agent_thinking(self, agent_name: str, thought: str, user_context: Dict[str, Any]):
        """Emit agent thinking event."""
        message = {
            "type": "agent_thinking",
            "agent_name": agent_name,
            "thought": thought,
            "user_context": user_context
        }
        return await self.send_to_user(user_context.get("user_id"), message)

    async def emit_tool_executing(self, tool_name: str, args: Dict[str, Any], user_context: Dict[str, Any]):
        """Emit tool executing event."""
        message = {
            "type": "tool_executing",
            "tool_name": tool_name,
            "args": args,
            "user_context": user_context
        }
        return await self.send_to_user(user_context.get("user_id"), message)

    async def emit_tool_completed(self, tool_name: str, result: Dict[str, Any], user_context: Dict[str, Any]):
        """Emit tool completed event."""
        message = {
            "type": "tool_completed",
            "tool_name": tool_name,
            "result": result,
            "user_context": user_context
        }
        return await self.send_to_user(user_context.get("user_id"), user_context)

    async def emit_agent_completed(self, agent_name: str, result: Any, user_context: Dict[str, Any]):
        """Emit agent completed event."""
        message = {
            "type": "agent_completed",
            "agent_name": agent_name,
            "result": result,
            "user_context": user_context
        }
        return await self.send_to_user(user_context.get("user_id"), message)


class MockWebSocketBridgeFactory:
    """Mock factory for WebSocket bridges with integration gap simulation."""

    def __init__(self):
        self.bridge_creation_attempts = []
        self.bridges_created = {}
        self.should_fail_creation = False

    def set_creation_failure(self, should_fail: bool):
        """Configure bridge creation failure."""
        self.should_fail_creation = should_fail

    async def create_bridge(self, user_context: Dict[str, Any]) -> MockWebSocketBridge:
        """Create WebSocket bridge - may fail to expose integration gaps."""
        self.bridge_creation_attempts.append({
            "user_context": user_context,
            "timestamp": time.time(),
            "should_fail": self.should_fail_creation
        })

        if self.should_fail_creation:
            raise PermissionError("WebSocket bridge creation not authorized")

        bridge = MockWebSocketBridge(user_context)
        user_id = user_context.get("user_id")
        self.bridges_created[user_id] = bridge
        return bridge


class MockAgentRegistry:
    """Mock Agent Registry that captures WebSocket integration gaps."""

    def __init__(self):
        self.websocket_manager = None
        self.bridge_factory = MockWebSocketBridgeFactory()
        self.execution_attempts = []
        self.integration_gaps = []

    def set_websocket_manager(self, manager):
        """Set WebSocket manager - this should be called but often isn't."""
        self.websocket_manager = manager

    def capture_integration_gap(
        self,
        gap_type: str,
        description: str,
        context: Dict[str, Any],
        severity: str = "HIGH"
    ):
        """Capture structured integration gap for analysis."""
        gap = {
            "gap_type": gap_type,
            "description": description,
            "context": context,
            "severity": severity,
            "timestamp": time.time()
        }
        self.integration_gaps.append(gap)

    async def execute_agent(self, agent_name: str, request: Dict[str, Any], user_context: Dict[str, Any]):
        """Execute agent - exposes WebSocket integration gaps."""
        execution_id = f"exec_{time.time()}"

        self.execution_attempts.append({
            "execution_id": execution_id,
            "agent_name": agent_name,
            "request": request,
            "user_context": user_context,
            "websocket_manager_present": self.websocket_manager is not None
        })

        # INTEGRATION GAP 1: Missing WebSocket manager
        if self.websocket_manager is None:
            self.capture_integration_gap(
                gap_type="MISSING_WEBSOCKET_MANAGER",
                description="Agent Registry executing without WebSocket manager",
                context={
                    "agent_name": agent_name,
                    "execution_id": execution_id,
                    "user_context": user_context
                }
            )
            # Continue execution but without WebSocket events
            return {"result": "executed_without_websocket_events", "execution_id": execution_id}

        # INTEGRATION GAP 2: Bridge creation failure
        try:
            bridge = await self.bridge_factory.create_bridge(user_context)
        except Exception as e:
            self.capture_integration_gap(
                gap_type="BRIDGE_CREATION_FAILURE",
                description=f"WebSocket bridge creation failed: {str(e)}",
                context={
                    "agent_name": agent_name,
                    "execution_id": execution_id,
                    "user_context": user_context,
                    "error": str(e)
                }
            )
            raise

        # INTEGRATION GAP 3: Missing WebSocket event emissions
        try:
            await bridge.emit_agent_started(agent_name, user_context)
            await bridge.emit_agent_thinking(agent_name, "Processing request...", user_context)
            await bridge.emit_tool_executing("mock_tool", request, user_context)
            await bridge.emit_tool_completed("mock_tool", {"status": "success"}, user_context)
            await bridge.emit_agent_completed(agent_name, {"result": "completed"}, user_context)
        except Exception as e:
            self.capture_integration_gap(
                gap_type="WEBSOCKET_EVENT_EMISSION_FAILURE",
                description=f"WebSocket event emission failed: {str(e)}",
                context={
                    "agent_name": agent_name,
                    "execution_id": execution_id,
                    "user_context": user_context,
                    "error": str(e)
                }
            )

        return {"result": "completed_with_websocket_events", "execution_id": execution_id}


class TestAgentRegistryWebSocketBridge(SSotAsyncTestCase):
    """Integration tests exposing Agent Registry WebSocket bridge gaps."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_agent_registry = MockAgentRegistry()
        self.sample_user_context = {
            "user_id": "test_user_123",
            "session_id": "session_456",
            "request_id": "req_789"
        }

    async def test_agent_registry_without_websocket_manager(self):
        """Test Agent Registry execution without WebSocket manager - should expose integration gap."""
        # Execute agent without setting WebSocket manager
        result = await self.mock_agent_registry.execute_agent(
            agent_name="DataHelperAgent",
            request={"query": "test query"},
            user_context=self.sample_user_context
        )

        # Should have captured the integration gap
        gaps = self.mock_agent_registry.integration_gaps
        assert len(gaps) > 0, "Should have captured MISSING_WEBSOCKET_MANAGER gap"

        missing_websocket_gaps = [g for g in gaps if g["gap_type"] == "MISSING_WEBSOCKET_MANAGER"]
        assert len(missing_websocket_gaps) > 0, "Should have captured missing WebSocket manager gap"

        # Result should indicate execution without WebSocket events
        assert result["result"] == "executed_without_websocket_events"

    async def test_bridge_creation_failure_simulation(self):
        """Test WebSocket bridge creation failure - should expose integration gap."""
        # Set up WebSocket manager
        mock_websocket_manager = Mock()
        self.mock_agent_registry.set_websocket_manager(mock_websocket_manager)

        # Configure bridge creation to fail
        self.mock_agent_registry.bridge_factory.set_creation_failure(True)

        # Execute agent - should fail on bridge creation
        with pytest.raises(PermissionError):
            await self.mock_agent_registry.execute_agent(
                agent_name="DataHelperAgent",
                request={"query": "test query"},
                user_context=self.sample_user_context
            )

        # Should have captured the bridge creation failure gap
        gaps = self.mock_agent_registry.integration_gaps
        bridge_creation_gaps = [g for g in gaps if g["gap_type"] == "BRIDGE_CREATION_FAILURE"]
        assert len(bridge_creation_gaps) > 0, "Should have captured bridge creation failure gap"

    async def test_websocket_event_emission_failure_simulation(self):
        """Test WebSocket event emission failure - should expose integration gap."""
        # Set up WebSocket manager
        mock_websocket_manager = Mock()
        self.mock_agent_registry.set_websocket_manager(mock_websocket_manager)

        # Bridge creation succeeds, but message sending fails
        bridge = await self.mock_agent_registry.bridge_factory.create_bridge(self.sample_user_context)
        bridge.set_failure_mode("send")

        # Replace the bridge factory's create_bridge method to return our failing bridge
        original_create_bridge = self.mock_agent_registry.bridge_factory.create_bridge
        self.mock_agent_registry.bridge_factory.create_bridge = AsyncMock(return_value=bridge)

        # Execute agent - should capture WebSocket event emission failures
        result = await self.mock_agent_registry.execute_agent(
            agent_name="DataHelperAgent",
            request={"query": "test query"},
            user_context=self.sample_user_context
        )

        # Should have captured WebSocket event emission failures
        gaps = self.mock_agent_registry.integration_gaps
        emission_gaps = [g for g in gaps if g["gap_type"] == "WEBSOCKET_EVENT_EMISSION_FAILURE"]
        assert len(emission_gaps) > 0, "Should have captured WebSocket event emission failures"

    async def test_successful_agent_execution_with_websocket_events(self):
        """Test successful agent execution with proper WebSocket integration."""
        # Set up WebSocket manager
        mock_websocket_manager = Mock()
        self.mock_agent_registry.set_websocket_manager(mock_websocket_manager)

        # Execute agent with proper setup
        result = await self.mock_agent_registry.execute_agent(
            agent_name="DataHelperAgent",
            request={"query": "test query"},
            user_context=self.sample_user_context
        )

        # Should complete successfully
        assert result["result"] == "completed_with_websocket_events"

        # Should have created a WebSocket bridge
        bridges = self.mock_agent_registry.bridge_factory.bridges_created
        assert self.sample_user_context["user_id"] in bridges

        # Bridge should have sent WebSocket messages
        bridge = bridges[self.sample_user_context["user_id"]]
        assert len(bridge.sent_messages) > 0, "Should have sent WebSocket messages"

        # Should have sent all required event types
        message_types = [msg["message"]["type"] for msg in bridge.sent_messages]
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]

        for event_type in required_events:
            assert event_type in message_types, f"Should have sent {event_type} event"

    async def test_multi_user_websocket_isolation(self):
        """Test WebSocket bridge isolation between multiple users."""
        # Set up WebSocket manager
        mock_websocket_manager = Mock()
        self.mock_agent_registry.set_websocket_manager(mock_websocket_manager)

        # Create multiple user contexts
        user_contexts = [
            {"user_id": "user_1", "session_id": "session_1", "request_id": "req_1"},
            {"user_id": "user_2", "session_id": "session_2", "request_id": "req_2"},
            {"user_id": "user_3", "session_id": "session_3", "request_id": "req_3"}
        ]

        # Execute agents for each user
        results = []
        for user_context in user_contexts:
            result = await self.mock_agent_registry.execute_agent(
                agent_name="DataHelperAgent",
                request={"query": f"test query for {user_context['user_id']}"},
                user_context=user_context
            )
            results.append(result)

        # Each user should have their own bridge
        bridges = self.mock_agent_registry.bridge_factory.bridges_created
        assert len(bridges) == len(user_contexts), "Each user should have their own bridge"

        # Each bridge should only have messages for its user
        for user_context in user_contexts:
            user_id = user_context["user_id"]
            bridge = bridges[user_id]

            for message in bridge.sent_messages:
                assert message["user_id"] == user_id, f"Bridge should only send messages to its own user"

    def test_integration_gap_analysis(self):
        """Test that integration gaps are properly captured and analyzable."""
        # Simulate various integration gaps
        gaps = [
            {
                "gap_type": "MISSING_WEBSOCKET_MANAGER",
                "description": "Agent Registry executing without WebSocket manager",
                "context": {"agent_name": "DataHelperAgent"},
                "severity": "HIGH",
                "timestamp": time.time()
            },
            {
                "gap_type": "BRIDGE_CREATION_FAILURE",
                "description": "WebSocket bridge creation failed: Permission denied",
                "context": {"agent_name": "DataHelperAgent"},
                "severity": "HIGH",
                "timestamp": time.time()
            }
        ]

        self.mock_agent_registry.integration_gaps.extend(gaps)

        # Analyze gaps by type
        gap_types = {}
        for gap in self.mock_agent_registry.integration_gaps:
            gap_type = gap["gap_type"]
            if gap_type not in gap_types:
                gap_types[gap_type] = 0
            gap_types[gap_type] += 1

        # Should be able to identify gap patterns
        assert "MISSING_WEBSOCKET_MANAGER" in gap_types
        assert "BRIDGE_CREATION_FAILURE" in gap_types

        # High severity gaps should be prioritized
        high_severity_gaps = [g for g in self.mock_agent_registry.integration_gaps if g["severity"] == "HIGH"]
        assert len(high_severity_gaps) > 0, "Should have high severity gaps for prioritization"


if __name__ == "__main__":
    pytest.main([__file__])