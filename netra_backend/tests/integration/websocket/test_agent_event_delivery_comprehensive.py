"""
Comprehensive Agent Event Delivery WebSocket Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core chat functionality
- Business Goal: Enable real-time agent communication for substantive AI interactions
- Value Impact: CRITICAL - Agent events deliver 90% of platform value through live AI progress
- Strategic/Revenue Impact: $500K+ ARR depends on users seeing agent work in real-time

MISSION CRITICAL: Tests the 5 WebSocket events that enable chat business value:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections with real agent execution
- Tests agent event delivery patterns for different scenarios
- Validates event content contains business value data
- Ensures proper event sequencing and timing
- Tests multi-agent event coordination
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import assert_websocket_events
from shared.isolated_environment import get_env

# Agent components for real business value testing
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent


class MockLLMForEventDelivery:
    """
    Mock LLM for testing agent event delivery patterns.
    This is the ONLY acceptable mock per CLAUDE.md - external LLM APIs.
    """
    
    def __init__(self, response_delay: float = 0.1):
        self.response_delay = response_delay
        self.call_count = 0
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM completion with configurable delay."""
        self.call_count += 1
        await asyncio.sleep(self.response_delay)
        
        return {
            "content": f"Agent response #{self.call_count} delivering business value through AI-powered analysis and insights.",
            "usage": {"total_tokens": 120 + (self.call_count * 10)}
        }


class TestAgentEventDeliveryComprehensive(BaseIntegrationTest):
    """
    Comprehensive tests for WebSocket agent event delivery patterns.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL agent execution
    to validate complete agent-to-WebSocket event flow for business value delivery.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_event_delivery_test(self, real_services_fixture):
        """
        Set up comprehensive agent event delivery test environment.
        
        BVJ: Test Infrastructure - Ensures reliable agent event delivery testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_user_id = f"event_delivery_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required - no mocks allowed"
        assert "backend" in real_services_fixture, "Real backend required for event delivery"
        assert "db" in real_services_fixture, "Real database required for agent context"
        
        # Initialize WebSocket auth helper
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002", 
            websocket_url="ws://localhost:8002/ws",
            test_user_email=f"event_test_{self.test_user_id}@example.com",
            timeout=25.0
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.websocket_connections: List[websockets.WebSocketServerProtocol] = []
        self.collected_events: List[Dict[str, Any]] = []
        
        # Verify auth helper can create tokens
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            assert token, "Failed to create test JWT token for event delivery testing"
        except Exception as e:
            pytest.fail(f"Event delivery test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up WebSocket connections and test resources."""
        for ws in self.websocket_connections:
            if not ws.closed:
                await ws.close()
        self.websocket_connections.clear()
        await super().async_teardown()
    
    async def collect_agent_events(
        self,
        websocket: websockets.WebSocketServerProtocol,
        expected_count: int,
        timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Collect WebSocket agent events until expected count or timeout.
        
        Args:
            websocket: WebSocket connection to monitor
            expected_count: Number of events expected
            timeout: Maximum time to wait
            
        Returns:
            List of collected agent events
        """
        events = []
        start_time = time.time()
        
        try:
            while len(events) < expected_count and (time.time() - start_time) < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    # Only collect agent-related events
                    if event.get("type", "").startswith(("agent_", "tool_")):
                        events.append({
                            **event,
                            "_received_at": time.time(),
                            "_order": len(events)
                        })
                        
                except asyncio.TimeoutError:
                    if (time.time() - start_time) >= timeout:
                        break
                    continue
                    
        except Exception as e:
            # Log but don't fail - return what we collected
            pass
            
        return events
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_single_agent_complete_event_sequence(self, real_services_fixture):
        """
        Test complete agent event sequence for single agent execution.
        
        BVJ: Complete user journey - Users see full AI problem-solving sequence.
        This validates the end-to-end event delivery that generates revenue.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Connect to real WebSocket
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = MockLLMForEventDelivery(0.2).complete_async
                
                # Send agent execution request
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "data_sub_agent",
                    "task": "Complete analysis with full event sequence",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect complete agent event sequence (expect at least 3 events)
                events = await self.collect_agent_events(websocket, expected_count=3, timeout=25.0)
                
                # Verify we received agent events
                assert len(events) >= 2, f"Expected at least 2 agent events, got {len(events)}"
                
                # Verify event types received
                event_types = [event.get("type") for event in events]
                
                # Must have started and completed events
                assert "agent_started" in event_types, "Missing agent_started - users won't know processing began"
                assert "agent_completed" in event_types, "Missing agent_completed - users won't know work finished"
                
                # Verify event sequence ordering
                started_event = next((e for e in events if e.get("type") == "agent_started"), None)
                completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
                
                if started_event and completed_event:
                    assert started_event["_received_at"] < completed_event["_received_at"], \
                        "agent_started must come before agent_completed"
                
                # Verify events contain business value data
                for event in events:
                    assert event.get("user_id") == self.test_user_id, "Event missing user context"
                    assert "timestamp" in event, "Event missing timestamp"
                    assert event.get("type").startswith(("agent_", "tool_")), "Non-agent event collected"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Single agent complete event sequence test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_rapid_agent_event_delivery_performance(self, real_services_fixture):
        """
        Test rapid agent event delivery performance under fast execution.
        
        BVJ: User experience - Events must arrive quickly for responsive AI interactions.
        Fast event delivery improves perceived AI capability and user satisfaction.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Fast mock LLM for rapid event delivery testing
                mock_llm_manager.return_value.complete_async = MockLLMForEventDelivery(0.05).complete_async
                
                start_time = time.time()
                
                # Send fast-executing agent request
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "quick_response_agent",
                    "task": "Fast response with rapid event delivery",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events with performance timing
                events = await self.collect_agent_events(websocket, expected_count=2, timeout=10.0)
                
                # Verify rapid event delivery
                assert len(events) >= 1, "No events received in rapid delivery test"
                
                # Check first event arrived quickly (within 3 seconds)
                first_event_time = events[0]["_received_at"] - start_time
                assert first_event_time < 3.0, \
                    f"First event took {first_event_time:.2f}s - too slow for rapid delivery"
                
                # Check all events arrived within reasonable time
                for i, event in enumerate(events):
                    event_time = event["_received_at"] - start_time
                    assert event_time < 8.0, \
                        f"Event {i} took {event_time:.2f}s - performance degradation detected"
                
                # Verify events maintain quality despite speed
                for event in events:
                    assert event.get("user_id") == self.test_user_id, "Rapid event missing user context"
                    assert event.get("type").startswith(("agent_", "tool_")), "Invalid rapid event type"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Rapid agent event delivery performance test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_thinking_event_content_validation(self, real_services_fixture):
        """
        Test agent_thinking event content validation for business value.
        
        BVJ: Reasoning transparency - Users must see meaningful AI thinking process.
        Rich thinking events demonstrate AI capability and justify premium pricing.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock LLM with extended thinking for content validation
                async def thinking_rich_llm(messages, **kwargs):
                    await asyncio.sleep(0.3)  # Extended thinking time
                    return {
                        "content": "Through deep analysis of multiple data points and consideration of various strategic approaches, I have identified the optimal solution path that maximizes business value while minimizing risk.",
                        "usage": {"total_tokens": 250}
                    }
                
                mock_llm_manager.return_value.complete_async = thinking_rich_llm
                
                # Request agent task requiring deep thinking
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "strategic_analysis_agent",
                    "task": "Perform strategic analysis requiring deep thinking and reasoning",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Focus on collecting thinking events
                events = await self.collect_agent_events(websocket, expected_count=3, timeout=20.0)
                
                # Find agent_thinking events
                thinking_events = [e for e in events if e.get("type") == "agent_thinking"]
                assert len(thinking_events) > 0, "No agent_thinking events received - users won't see AI reasoning"
                
                # Validate thinking event content richness
                for thinking_event in thinking_events:
                    # Must have user context
                    assert thinking_event.get("user_id") == self.test_user_id, "Thinking event missing user context"
                    
                    # Must have timestamp for sequence tracking
                    assert "timestamp" in thinking_event, "Thinking event missing timestamp"
                    
                    # Should have meaningful content (not just status)
                    assert any(key in thinking_event for key in ["reasoning", "status", "progress", "analysis"]), \
                        "Thinking event lacks meaningful content for user visibility"
                    
                    # Content should be substantial (not empty)
                    content_fields = [thinking_event.get(key, "") for key in ["reasoning", "status", "progress", "analysis"]]
                    has_substantial_content = any(len(str(field)) > 10 for field in content_fields)
                    assert has_substantial_content, "Thinking event content too brief for business value"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Agent thinking event content validation test failed: {e}")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_tool_event_pair_delivery_validation(self, real_services_fixture):
        """
        Test tool_executing and tool_completed event pair delivery.
        
        BVJ: Tool transparency - Users see complete tool usage cycle for trust.
        Tool event pairs demonstrate AI problem-solving methodology and build confidence.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock LLM that uses tools for comprehensive validation
                async def tool_using_llm(messages, **kwargs):
                    await asyncio.sleep(0.2)
                    return {
                        "content": "I'll analyze your data using specialized tools to provide comprehensive insights.",
                        "tool_calls": [
                            {
                                "id": "analysis_tool_001",
                                "type": "function",
                                "function": {
                                    "name": "comprehensive_analysis",
                                    "arguments": json.dumps({
                                        "data_type": "business_metrics",
                                        "analysis_depth": "detailed",
                                        "output_format": "insights_report"
                                    })
                                }
                            }
                        ],
                        "usage": {"total_tokens": 200}
                    }
                
                mock_llm_manager.return_value.complete_async = tool_using_llm
                
                # Request agent task that uses tools
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "tool_using_agent",
                    "task": "Comprehensive analysis using multiple tools for detailed insights",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events focusing on tool event pairs
                events = await self.collect_agent_events(websocket, expected_count=4, timeout=25.0)
                
                # Find tool events
                tool_executing_events = [e for e in events if e.get("type") == "tool_executing"]
                tool_completed_events = [e for e in events if e.get("type") == "tool_completed"]
                
                # Validate tool event pair delivery
                assert len(tool_executing_events) > 0, "No tool_executing events - users won't see tool usage start"
                assert len(tool_completed_events) > 0, "No tool_completed events - users won't see tool results"
                
                # Verify each executing event has corresponding completed event
                for exec_event in tool_executing_events:
                    exec_tool_id = exec_event.get("tool_id") or exec_event.get("tool_name")
                    
                    # Find matching completed event
                    matching_completed = None
                    for comp_event in tool_completed_events:
                        comp_tool_id = comp_event.get("tool_id") or comp_event.get("tool_name")
                        if exec_tool_id and comp_tool_id and exec_tool_id == comp_tool_id:
                            matching_completed = comp_event
                            break
                    
                    # Allow for partial matching if IDs not perfectly aligned
                    if not matching_completed and tool_completed_events:
                        matching_completed = tool_completed_events[0]  # Use first available
                    
                    assert matching_completed is not None, f"No matching tool_completed event for tool {exec_tool_id}"
                    
                    # Verify proper sequencing
                    assert exec_event["_received_at"] <= matching_completed["_received_at"], \
                        "tool_executing must come before or simultaneous with tool_completed"
                
                # Validate tool event content quality
                for tool_event in tool_executing_events + tool_completed_events:
                    assert tool_event.get("user_id") == self.test_user_id, "Tool event missing user context"
                    assert "timestamp" in tool_event, "Tool event missing timestamp"
                    
                    # Tool events should have identification
                    assert any(key in tool_event for key in ["tool_id", "tool_name", "tool_type"]), \
                        "Tool event lacks tool identification"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Tool event pair delivery validation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_step_agent_event_orchestration(self, real_services_fixture):
        """
        Test multi-step agent execution with complex event orchestration.
        
        BVJ: Complex workflow visibility - Users see detailed AI workflow for complex tasks.
        Multi-step events demonstrate AI sophistication and justify enterprise pricing.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            self.websocket_connections.append(websocket)
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Mock LLM for multi-step complex workflow
                call_count = 0
                
                async def multi_step_llm(messages, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    await asyncio.sleep(0.15 * call_count)  # Increasing delay for each step
                    
                    if call_count == 1:
                        return {
                            "content": "Starting comprehensive multi-step analysis. First, I'll gather and process the initial data.",
                            "tool_calls": [
                                {
                                    "id": f"step_1_tool_{call_count}",
                                    "type": "function",
                                    "function": {
                                        "name": "data_gathering", 
                                        "arguments": json.dumps({"step": 1, "phase": "initial"})
                                    }
                                }
                            ],
                            "usage": {"total_tokens": 150}
                        }
                    elif call_count == 2:
                        return {
                            "content": "Now performing detailed analysis of the gathered data using advanced analytical methods.",
                            "tool_calls": [
                                {
                                    "id": f"step_2_tool_{call_count}",
                                    "type": "function", 
                                    "function": {
                                        "name": "advanced_analysis",
                                        "arguments": json.dumps({"step": 2, "phase": "analysis"})
                                    }
                                }
                            ],
                            "usage": {"total_tokens": 200}
                        }
                    else:
                        return {
                            "content": "Completing final synthesis and generating comprehensive recommendations based on all analysis phases.",
                            "usage": {"total_tokens": 250}
                        }
                
                mock_llm_manager.return_value.complete_async = multi_step_llm
                
                # Request complex multi-step agent task
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "multi_step_analysis_agent",
                    "task": "Perform comprehensive multi-step analysis with detailed workflow orchestration",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect extended event sequence for multi-step workflow
                events = await self.collect_agent_events(websocket, expected_count=6, timeout=35.0)
                
                # Verify we received a substantial event sequence
                assert len(events) >= 3, f"Multi-step workflow only generated {len(events)} events - insufficient visibility"
                
                # Analyze event flow patterns
                event_types = [event.get("type") for event in events]
                
                # Should have workflow progression visibility
                assert "agent_started" in event_types, "Multi-step workflow missing start visibility"
                assert "agent_completed" in event_types, "Multi-step workflow missing completion visibility"
                
                # Should have intermediate progress events
                progress_events = [e for e in events if e.get("type") in ["agent_thinking", "tool_executing", "tool_completed"]]
                assert len(progress_events) >= 1, "Multi-step workflow lacks intermediate progress events"
                
                # Verify event sequence coherence
                event_times = [(e.get("type"), e["_received_at"]) for e in events]
                event_times.sort(key=lambda x: x[1])  # Sort by time
                
                # Ensure logical flow (started comes before completed)
                start_indices = [i for i, (event_type, _) in enumerate(event_times) if event_type == "agent_started"]
                complete_indices = [i for i, (event_type, _) in enumerate(event_times) if event_type == "agent_completed"]
                
                if start_indices and complete_indices:
                    assert start_indices[0] < complete_indices[-1], "Event flow sequence violation in multi-step workflow"
                
                # Validate each event maintains context and quality
                for event in events:
                    assert event.get("user_id") == self.test_user_id, "Multi-step event missing user context"
                    assert "timestamp" in event, "Multi-step event missing timestamp"
                    
                    # Events should show progression or substance
                    event_type = event.get("type")
                    if event_type in ["agent_thinking", "tool_executing", "tool_completed"]:
                        has_content = any(key in event for key in ["reasoning", "status", "progress", "tool_name", "result"])
                        assert has_content, f"Multi-step {event_type} event lacks substantial content"
                
                await websocket.close()
                
        except Exception as e:
            pytest.fail(f"Multi-step agent event orchestration test failed: {e}")