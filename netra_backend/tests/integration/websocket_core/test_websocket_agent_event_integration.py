#!/usr/bin/env python
"""
Integration Tests for WebSocket Agent Event Delivery

MISSION CRITICAL: Real WebSocket integration tests for chat functionality.
Tests real WebSocket connections with agent event delivery for business value.

Business Value: $500K+ ARR - Real-time chat integration validation
- Tests real WebSocket connections (no mocks) with agent events
- Validates end-to-end event delivery from agents to WebSocket clients
- Ensures all 5 REQUIRED events work with real WebSocket infrastructure
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType

# Import production WebSocket components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.llm.llm_manager import LLMManager


@pytest.fixture
async def real_websocket_utility():
    """Create real WebSocket test utility - NO MOCKS per CLAUDE.md."""
    async with WebSocketTestUtility() as ws_util:
        yield ws_util


@pytest.fixture
def sample_user_context():
    """Create user execution context for integration testing."""
    return UserExecutionContext(
        user_id=UserID(f"integration_user_{uuid.uuid4().hex[:8]}"),
        thread_id=ThreadID(f"integration_thread_{uuid.uuid4().hex[:8]}"),
        request_id=RequestID(f"integration_request_{uuid.uuid4().hex[:8]}"),
        session_id=f"integration_session_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
async def real_websocket_manager():
    """Create real UnifiedWebSocketManager for integration testing."""
    manager = UnifiedWebSocketManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.mark.integration
class TestRealWebSocketAgentEvents:
    """Integration tests for real WebSocket agent event delivery."""
    
    @pytest.mark.asyncio
    async def test_real_websocket_agent_started_event_delivery(self, real_websocket_utility, real_websocket_manager, sample_user_context):
        """
        Test real WebSocket delivery of agent_started event.
        
        CRITICAL: agent_started event must reach real WebSocket clients.
        This is the first event users see when agents begin processing.
        """
        # Arrange
        bridge = AgentWebSocketBridge(real_websocket_manager)
        
        async with real_websocket_utility.connected_client(sample_user_context.user_id) as client:
            # Simulate WebSocket connection registration
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id, 
                client.websocket
            )
            
            # Create agent_started event
            agent_data = {
                "agent": "triage_agent",
                "status": "starting", 
                "timestamp": datetime.now().isoformat(),
                "user_request": "Analyze optimization opportunities"
            }
            
            # Act
            result = await bridge.emit_event(
                context=sample_user_context,
                event_type="agent_started",
                event_data=agent_data
            )
            
            # Assert
            assert result is True, "Agent started event must be emitted successfully"
            
            # Wait for and verify real WebSocket message
            received_message = await client.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            
            assert received_message is not None, "Must receive agent_started event"
            assert received_message.event_type == TestEventType.AGENT_STARTED
            assert received_message.data["agent"] == "triage_agent"
            assert received_message.data["status"] == "starting"
            assert received_message.user_id == sample_user_context.user_id
    
    @pytest.mark.asyncio
    async def test_real_websocket_tool_execution_event_flow(self, real_websocket_utility, real_websocket_manager, sample_user_context):
        """
        Test real WebSocket delivery of tool execution events (tool_executing + tool_completed).
        
        CRITICAL: Tool execution events provide transparency and actionable insights.
        Users must see tools being executed and their results for business value.
        """
        # Arrange
        bridge = AgentWebSocketBridge(real_websocket_manager)
        
        async with real_websocket_utility.connected_client(sample_user_context.user_id) as client:
            # Register client connection
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id,
                client.websocket
            )
            
            # Tool execution data
            tool_name = "cost_optimization_analyzer"
            tool_args = {
                "timeframe": "last_30_days",
                "categories": ["compute", "storage", "network"],
                "threshold": 1000
            }
            tool_result = {
                "analysis": "Found 3 optimization opportunities",
                "potential_savings": 15000,
                "recommendations": [
                    "Optimize unused compute resources",
                    "Implement intelligent storage tiering", 
                    "Reduce network overhead"
                ],
                "confidence_score": 0.94
            }
            
            # Act - Emit tool_executing event
            executing_result = await bridge.emit_event(
                context=sample_user_context,
                event_type="tool_executing",
                event_data={
                    "tool": tool_name,
                    "args": tool_args,
                    "status": "executing",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Act - Emit tool_completed event
            completed_result = await bridge.emit_event(
                context=sample_user_context,
                event_type="tool_completed",
                event_data={
                    "tool": tool_name,
                    "result": tool_result,
                    "status": "completed",
                    "execution_time_ms": 3500,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Assert
            assert executing_result is True, "Tool executing event must be emitted"
            assert completed_result is True, "Tool completed event must be emitted"
            
            # Wait for both events
            expected_events = [TestEventType.TOOL_EXECUTING, TestEventType.TOOL_COMPLETED]
            received_events = await client.wait_for_events(expected_events, timeout=15.0)
            
            # Verify tool_executing event
            executing_messages = received_events[TestEventType.TOOL_EXECUTING]
            assert len(executing_messages) > 0, "Must receive tool_executing event"
            executing_msg = executing_messages[0]
            assert executing_msg.data["tool"] == tool_name
            assert executing_msg.data["status"] == "executing"
            assert executing_msg.data["args"] == tool_args
            
            # Verify tool_completed event
            completed_messages = received_events[TestEventType.TOOL_COMPLETED]
            assert len(completed_messages) > 0, "Must receive tool_completed event"
            completed_msg = completed_messages[0]
            assert completed_msg.data["tool"] == tool_name
            assert completed_msg.data["status"] == "completed"
            assert completed_msg.data["result"]["potential_savings"] == 15000
            assert len(completed_msg.data["result"]["recommendations"]) == 3
    
    @pytest.mark.asyncio
    async def test_real_websocket_complete_agent_workflow(self, real_websocket_utility, real_websocket_manager, sample_user_context):
        """
        Test complete agent workflow with all 5 REQUIRED WebSocket events.
        
        CRITICAL: Complete workflow tests full chat value delivery chain.
        All 5 events must work together for substantive AI interaction.
        """
        # Arrange
        bridge = AgentWebSocketBridge(real_websocket_manager)
        
        async with real_websocket_utility.connected_client(sample_user_context.user_id) as client:
            # Register client connection
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id,
                client.websocket
            )
            
            # Simulate complete agent workflow
            workflow_events = [
                ("agent_started", {
                    "agent": "optimization_agent",
                    "status": "starting",
                    "user_request": "Find cost optimization opportunities"
                }),
                ("agent_thinking", {
                    "agent": "optimization_agent", 
                    "progress": "Analyzing current infrastructure costs",
                    "stage": "data_collection"
                }),
                ("tool_executing", {
                    "tool": "cost_analyzer",
                    "status": "executing",
                    "description": "Analyzing cost patterns"
                }),
                ("tool_completed", {
                    "tool": "cost_analyzer",
                    "result": {
                        "monthly_cost": 25000,
                        "optimization_potential": 8000,
                        "categories_analyzed": ["compute", "storage", "network"]
                    },
                    "status": "completed"
                }),
                ("agent_completed", {
                    "agent": "optimization_agent",
                    "result": {
                        "summary": "Found $8,000/month in optimization opportunities",
                        "action_items": 3,
                        "confidence": 0.92,
                        "next_steps": ["implement_recommendations", "monitor_savings"]
                    },
                    "status": "completed"
                })
            ]
            
            # Act - Emit all events in sequence
            for event_type, event_data in workflow_events:
                event_data["timestamp"] = datetime.now().isoformat()
                result = await bridge.emit_event(
                    context=sample_user_context,
                    event_type=event_type,
                    event_data=event_data
                )
                assert result is True, f"Event {event_type} must be emitted successfully"
                
                # Small delay between events to simulate real agent execution
                await asyncio.sleep(0.5)
            
            # Assert - Wait for all events
            expected_event_types = [
                TestEventType.AGENT_STARTED,
                TestEventType.AGENT_THINKING, 
                TestEventType.TOOL_EXECUTING,
                TestEventType.TOOL_COMPLETED,
                TestEventType.AGENT_COMPLETED
            ]
            
            received_events = await client.wait_for_events(expected_event_types, timeout=20.0)
            
            # Verify all 5 REQUIRED events were received
            for event_type in expected_event_types:
                assert event_type in received_events, f"Must receive {event_type.value} event"
                assert len(received_events[event_type]) > 0, f"Must have at least one {event_type.value} event"
            
            # Verify event content integrity
            agent_started = received_events[TestEventType.AGENT_STARTED][0]
            assert agent_started.data["agent"] == "optimization_agent"
            
            agent_completed = received_events[TestEventType.AGENT_COMPLETED][0]
            assert agent_completed.data["result"]["confidence"] == 0.92
            assert agent_completed.data["result"]["action_items"] == 3
    
    @pytest.mark.asyncio
    async def test_real_websocket_multi_user_event_isolation(self, real_websocket_utility, real_websocket_manager):
        """
        Test real WebSocket multi-user event isolation.
        
        CRITICAL: Multi-user isolation prevents cross-user event contamination.
        Breaking this breaks security and user experience in multi-tenant system.
        """
        # Arrange - Create contexts for two different users
        user1_context = UserExecutionContext(
            user_id=UserID(f"isolation_user1_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"isolation_thread1_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"isolation_request1_{uuid.uuid4().hex[:8]}")
        )
        
        user2_context = UserExecutionContext(
            user_id=UserID(f"isolation_user2_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"isolation_thread2_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"isolation_request2_{uuid.uuid4().hex[:8]}")
        )
        
        bridge = AgentWebSocketBridge(real_websocket_manager)
        
        # Create separate WebSocket clients for each user
        async with real_websocket_utility.connected_client(user1_context.user_id) as client1, \
                   real_websocket_utility.connected_client(user2_context.user_id) as client2:
            
            # Register both client connections
            await real_websocket_manager.register_user_connection(user1_context.user_id, client1.websocket)
            await real_websocket_manager.register_user_connection(user2_context.user_id, client2.websocket)
            
            # Act - Send events to each user
            user1_event = {
                "agent": "user1_agent",
                "status": "starting",
                "user_data": "confidential_user1_info",
                "timestamp": datetime.now().isoformat()
            }
            
            user2_event = {
                "agent": "user2_agent", 
                "status": "starting",
                "user_data": "confidential_user2_info",
                "timestamp": datetime.now().isoformat()
            }
            
            # Emit events for each user
            result1 = await bridge.emit_event(
                context=user1_context,
                event_type="agent_started",
                event_data=user1_event
            )
            
            result2 = await bridge.emit_event(
                context=user2_context,
                event_type="agent_started", 
                event_data=user2_event
            )
            
            assert result1 is True, "User1 event must be emitted"
            assert result2 is True, "User2 event must be emitted"
            
            # Assert - Verify isolation
            # Wait for events on each client
            user1_received = await client1.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            
            user2_received = await client2.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            
            # Verify each user only received their own event
            assert user1_received.data["agent"] == "user1_agent"
            assert user1_received.data["user_data"] == "confidential_user1_info"
            assert user1_received.user_id == user1_context.user_id
            
            assert user2_received.data["agent"] == "user2_agent"
            assert user2_received.data["user_data"] == "confidential_user2_info"
            assert user2_received.user_id == user2_context.user_id
            
            # Verify no cross-contamination
            # Check that client1 didn't receive user2's data
            assert user1_received.data["user_data"] != "confidential_user2_info"
            assert user2_received.data["user_data"] != "confidential_user1_info"


@pytest.mark.integration
class TestWebSocketAgentRegistryIntegration:
    """Integration tests for WebSocket integration with AgentRegistry."""
    
    @pytest.mark.asyncio
    async def test_agent_registry_websocket_integration(self, real_websocket_utility, real_websocket_manager, sample_user_context):
        """
        Test AgentRegistry integration with WebSocket manager.
        
        CRITICAL: AgentRegistry must properly wire WebSocket events to agents.
        This integration enables agents to send real-time updates to users.
        """
        # Arrange
        mock_llm_manager = MagicMock(spec=LLMManager)
        registry = AgentRegistry(mock_llm_manager)
        
        # Set WebSocket manager on registry
        await registry.set_websocket_manager_async(real_websocket_manager)
        
        async with real_websocket_utility.connected_client(sample_user_context.user_id) as client:
            # Register client connection
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id,
                client.websocket
            )
            
            # Act - Get user session with WebSocket bridge
            user_session = await registry.get_user_session(sample_user_context.user_id)
            
            # Assert
            assert user_session is not None, "Must get user session"
            assert user_session._websocket_bridge is not None, "User session must have WebSocket bridge"
            
            # Test event emission through user session bridge
            bridge = user_session._websocket_bridge
            result = await bridge.emit_event(
                context=sample_user_context,
                event_type="agent_started",
                event_data={
                    "agent": "registry_test_agent",
                    "status": "starting",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            assert result is True, "Event must be emitted through registry bridge"
            
            # Verify real WebSocket reception
            received_message = await client.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            
            assert received_message is not None, "Must receive event through registry integration"
            assert received_message.data["agent"] == "registry_test_agent"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle_integration(self, real_websocket_utility, real_websocket_manager, sample_user_context):
        """
        Test WebSocket connection lifecycle integration with agent events.
        
        CRITICAL: Connection lifecycle must not disrupt agent event delivery.
        Reconnections and failures must be handled gracefully.
        """
        # Arrange
        bridge = AgentWebSocketBridge(real_websocket_manager)
        
        async with real_websocket_utility.connected_client(sample_user_context.user_id) as client:
            # Initial connection and event
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id,
                client.websocket
            )
            
            # Send initial event
            result1 = await bridge.emit_event(
                context=sample_user_context,
                event_type="agent_started",
                event_data={
                    "agent": "lifecycle_test_agent",
                    "status": "starting",
                    "phase": "initial"
                }
            )
            
            assert result1 is True, "Initial event must be sent"
            
            # Verify initial event reception
            initial_message = await client.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            assert initial_message.data["phase"] == "initial"
            
            # Simulate connection disconnection and reconnection
            await client.disconnect()
            await asyncio.sleep(1.0)  # Brief disconnect period
            
            # Reconnect
            reconnected = await client.connect()
            assert reconnected is True, "Client must reconnect successfully"
            
            # Re-register connection
            await real_websocket_manager.register_user_connection(
                sample_user_context.user_id,
                client.websocket
            )
            
            # Send event after reconnection
            result2 = await bridge.emit_event(
                context=sample_user_context,
                event_type="agent_thinking",
                event_data={
                    "agent": "lifecycle_test_agent",
                    "progress": "continuing after reconnection",
                    "phase": "reconnected"
                }
            )
            
            assert result2 is True, "Event after reconnection must be sent"
            
            # Verify reconnected event reception
            reconnect_message = await client.wait_for_message(
                event_type=TestEventType.AGENT_THINKING,
                timeout=10.0
            )
            assert reconnect_message.data["phase"] == "reconnected"